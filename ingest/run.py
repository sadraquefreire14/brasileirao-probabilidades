"""Ponto de entrada: busca partidas, simula e grava os JSONs consumidos pelo Astro.

Uso:
    python -m ingest.run                       # API football-data.org (FOOTBALL_DATA_TOKEN)
    python -m ingest.run --fixture fixtures/sample_matches.json   # offline / desenvolvimento
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .config import HISTORY_FILE, SETTINGS, SNAPSHOT_FILE, Settings
from .model import fit, outcome_probs
from .models import Match, parse_match
from .simulate import simulate
from .table import build_table

log = logging.getLogger("ingest")
HISTORY_MIN_PROB = 0.001  # não guarda probabilidades desprezíveis no histórico


def load_matches(settings: Settings, fixture: Path | None) -> list[Match]:
    if fixture:
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        return [parse_match(m) for m in payload["matches"]]
    from .client import fetch_matches  # import tardio: modo offline não precisa de httpx
    return fetch_matches(settings)


def build_snapshot(matches: list[Match], settings: Settings, sample: bool) -> dict:
    table = build_table(matches)
    if len(table) != settings.n_teams:
        log.warning("Esperados %s times, encontrados %s", settings.n_teams, len(table))

    pending = [m for m in matches if m.pending]
    played = [m for m in matches if m.played]
    team_ids = [r.team.id for r in table]
    strengths = fit(matches, team_ids, settings.half_life_matchdays, settings.prior_matches)
    sim = simulate(table, pending, strengths, settings.n_sims, settings.seed)

    n, lib, rel = len(table), settings.libertadores_direct, settings.relegated
    teams = []
    for i, row in enumerate(table):
        probs = sim.position_probs[i]
        teams.append({
            "pos": i + 1,
            "id": row.team.id,
            "name": row.team.name,
            "short": row.team.short,
            "crest": row.team.crest,
            "j": row.j, "v": row.v, "e": row.e, "d": row.d,
            "gp": row.gp, "gc": row.gc, "sg": row.sg, "pts": row.pts,
            "form": row.form[-5:],
            "p_title": round(float(probs[0]), 5),
            "p_lib": round(float(probs[:lib].sum()), 5),
            "p_rel": round(float(probs[n - rel:].sum()), 5),
            "exp_pts": round(float(sim.expected_points[i]), 1),
            "pos_probs": [round(float(p), 4) for p in probs],
            "attack": round(float(strengths.attack[i]), 3),
            "defense": round(float(strengths.defense[i]), 3),
        })

    upcoming = sorted(pending, key=lambda m: m.utc_date)[:10]
    next_matches = []
    for m in upcoming:
        lh, la = strengths.rates(m.home.id, m.away.id)
        ph, pd, pa = outcome_probs(lh, la)
        next_matches.append({
            "utc_date": m.utc_date, "matchday": m.matchday, "status": m.status,
            "home": m.home.short, "away": m.away.short,
            "home_crest": m.home.crest, "away_crest": m.away.crest,
            "p_home": round(ph, 4), "p_draw": round(pd, 4), "p_away": round(pa, 4),
        })

    rodada = max((m.matchday or 0 for m in played), default=0)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "season": settings.season,
        "sample": sample,
        "rodada": rodada,
        "played": len(played),
        "remaining": len(pending),
        "n_sims": sim.n_sims,
        "rules": {"teams": n, "libertadores_direct": lib, "relegated": rel},
        "model": {
            "mu_home": round(strengths.mu_home, 3),
            "mu_away": round(strengths.mu_away, 3),
            "half_life_matchdays": settings.half_life_matchdays,
        },
        "teams": teams,
        "next_matches": next_matches,
    }


def update_history(history: list[dict], snap: dict) -> list[dict]:
    """Um ponto por rodada: a execução mais recente de uma rodada substitui a anterior."""
    entry = {
        "rodada": snap["rodada"],
        "at": snap["generated_at"],
        "sample": snap["sample"],
        "title": {t["short"]: t["p_title"] for t in snap["teams"] if t["p_title"] >= HISTORY_MIN_PROB},
        "rel": {t["short"]: t["p_rel"] for t in snap["teams"] if t["p_rel"] >= HISTORY_MIN_PROB},
    }
    kept = [h for h in history if h["rodada"] != entry["rodada"]]
    return sorted(kept + [entry], key=lambda h: h["rodada"])


def write_json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.chmod(tmp, 0o644)  # mkstemp cria com 0600
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixture", type=Path, help="JSON no formato da API (modo offline)")
    ap.add_argument("--sims", type=int, help="número de simulações")
    ap.add_argument("--seed", type=int, help="semente para resultados reprodutíveis")
    args = ap.parse_args(argv)

    settings = SETTINGS
    if args.sims or args.seed is not None:
        settings = replace(settings, n_sims=args.sims or settings.n_sims, seed=args.seed)

    matches = load_matches(settings, args.fixture)
    if not matches:
        log.error("Nenhuma partida retornada; mantendo os dados anteriores.")
        return 1

    snap = build_snapshot(matches, settings, sample=args.fixture is not None)
    history = json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else []
    if args.fixture is None:
        history = [h for h in history if not h.get("sample")]
    write_json_atomic(SNAPSHOT_FILE, snap)
    write_json_atomic(HISTORY_FILE, update_history(history, snap))

    leader = snap["teams"][0]
    log.info("Rodada %s | %s jogos restantes | líder %s (título %.1f%%)",
             snap["rodada"], snap["remaining"], leader["short"], 100 * leader["p_title"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
