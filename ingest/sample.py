"""Gera um campeonato fictício no formato da API, para desenvolver sem token.

    python -m ingest.sample --played 33 > fixtures/sample_matches.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

TEAMS = [
    "Time Azul", "Time Verde", "Time Vermelho", "Time Preto", "Time Branco",
    "Time Amarelo", "Time Laranja", "Time Roxo", "Time Cinza", "Time Dourado",
    "Time Prata", "Time Marrom", "Time Rosa", "Time Celeste", "Time Grená",
    "Time Vinho", "Time Lilás", "Time Bege", "Time Turquesa", "Time Coral",
]


def round_robin(n: int) -> list[list[tuple[int, int]]]:
    """Método do círculo: turno + returno com mandos invertidos."""
    teams = list(range(n))
    first = []
    for r in range(n - 1):
        pairs = [(teams[i], teams[n - 1 - i]) for i in range(n // 2)]
        first.append([(a, b) if r % 2 == 0 else (b, a) for a, b in pairs])
        teams = [teams[0], teams[-1], *teams[1:-1]]
    return first + [[(b, a) for a, b in rnd] for rnd in first]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--played", type=int, default=33)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)

    rng = np.random.default_rng(args.seed)
    strength = np.sort(rng.normal(0, 0.28, len(TEAMS)))[::-1]
    start = datetime(2026, 4, 1, 22, tzinfo=timezone.utc)
    matches, mid = [], 1
    for md, rnd in enumerate(round_robin(len(TEAMS)), start=1):
        for h, a in rnd:
            played = md <= args.played
            lh = 1.45 * np.exp(strength[h] - strength[a] * 0.8)
            la = 1.05 * np.exp(strength[a] - strength[h] * 0.8)
            matches.append({
                "id": mid, "matchday": md,
                "utcDate": (start + timedelta(days=7 * (md - 1))).isoformat().replace("+00:00", "Z"),
                "status": "FINISHED" if played else "TIMED",
                "homeTeam": {"id": h + 1, "name": TEAMS[h], "shortName": TEAMS[h]},
                "awayTeam": {"id": a + 1, "name": TEAMS[a], "shortName": TEAMS[a]},
                "score": {"fullTime": {"home": int(rng.poisson(lh)), "away": int(rng.poisson(la))}
                          if played else {"home": None, "away": None}},
            })
            mid += 1
    json.dump({"matches": matches}, sys.stdout)  # ASCII: independe do encoding do terminal
    return 0


if __name__ == "__main__":
    sys.exit(main())
