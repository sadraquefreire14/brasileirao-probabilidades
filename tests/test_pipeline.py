import numpy as np
import pytest

from ingest.config import SETTINGS
from ingest.model import fit, outcome_probs
from ingest.models import parse_match
from ingest.run import build_snapshot, update_history
from ingest.sample import round_robin
from ingest.table import build_table


def raw(mid, md, h, a, hg=None, ag=None, status="FINISHED"):
    return {
        "id": mid, "matchday": md, "utcDate": f"2026-05-{md:02d}T20:00:00Z", "status": status,
        "homeTeam": {"id": h, "name": f"T{h}", "shortName": f"T{h}"},
        "awayTeam": {"id": a, "name": f"T{a}", "shortName": f"T{a}"},
        "score": {"fullTime": {"home": hg, "away": ag}},
    }


def test_table_points_and_tiebreak():
    ms = [parse_match(m) for m in [
        raw(1, 1, 1, 2, 2, 0), raw(2, 1, 3, 4, 1, 1),
        raw(3, 2, 2, 3, 3, 0), raw(4, 2, 4, 1, 0, 0),
        raw(5, 3, 1, 3, None, None, "TIMED"),
    ]]
    t = build_table(ms)
    by = {r.team.id: r for r in t}
    assert by[1].pts == 4 and by[1].j == 2 and by[1].sg == 2
    assert by[2].pts == 3 and by[2].sg == 1
    assert [r.team.id for r in t][0] == 1
    assert by[1].form == ["V", "E"]


def test_round_robin_complete():
    rounds = round_robin(20)
    assert len(rounds) == 38
    pairs = [p for r in rounds for p in r]
    assert len(pairs) == 380 and len(set(pairs)) == 380  # cada mando uma vez
    for r in rounds:
        teams = [t for p in r for t in p]
        assert sorted(teams) == list(range(20))


def test_outcome_probs_sum_to_one():
    ph, pd, pa = outcome_probs(1.6, 0.9)
    assert ph + pd + pa == pytest.approx(1.0)
    assert ph > pa


def _sample_matches(played):
    from ingest import sample
    import io, json, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sample.main(["--played", str(played)])
    return [parse_match(m) for m in json.loads(buf.getvalue())["matches"]]


def test_snapshot_probabilities_consistent():
    from dataclasses import replace
    settings = replace(SETTINGS, n_sims=4000, seed=1)
    snap = build_snapshot(_sample_matches(33), settings, sample=True)
    teams = snap["teams"]
    assert len(teams) == 20 and snap["remaining"] == 50
    assert sum(t["p_title"] for t in teams) == pytest.approx(1.0, abs=1e-3)
    assert sum(t["p_rel"] for t in teams) == pytest.approx(4.0, abs=1e-2)
    assert sum(t["p_lib"] for t in teams) == pytest.approx(5.0, abs=1e-2)
    for t in teams:
        assert sum(t["pos_probs"]) == pytest.approx(1.0, abs=2e-3)
    # o líder deve ter mais chance de título que o último
    assert teams[0]["p_title"] > teams[-1]["p_title"]


def test_finished_season_is_deterministic():
    from dataclasses import replace
    snap = build_snapshot(_sample_matches(38), replace(SETTINGS, n_sims=500, seed=2), sample=True)
    assert snap["remaining"] == 0
    assert snap["teams"][0]["p_title"] == 1.0
    assert all(t["p_rel"] == 1.0 for t in snap["teams"][-4:])


def test_history_upsert_by_round():
    snap = {"rodada": 10, "generated_at": "x", "sample": False,
            "teams": [{"short": "A", "p_title": 0.5, "p_rel": 0.0}]}
    h = update_history([{"rodada": 10, "at": "old"}, {"rodada": 9, "at": "y"}], snap)
    assert [e["rodada"] for e in h] == [9, 10] and h[-1]["at"] == "x"
    assert "A" not in h[-1]["rel"]


def test_fit_shrinks_without_data():
    s = fit([], [1, 2], 12, 6)
    assert np.allclose(s.attack, 1) and np.allclose(s.defense, 1)


def test_next_matches_carry_crests():
    home = raw(1, 1, 1, 2, status="TIMED")
    home["homeTeam"]["crest"] = "https://crests.football-data.org/1.png"
    ms = [parse_match(m) for m in [raw(2, 1, 3, 4, 1, 0), home]]
    snap = build_snapshot(ms, SETTINGS, sample=True)
    nxt = snap["next_matches"][0]
    assert nxt["home_crest"] == "https://crests.football-data.org/1.png"
    assert nxt["away_crest"] is None
    assert {t["short"]: t["crest"] for t in snap["teams"]}["T1"] == home["homeTeam"]["crest"]


def test_short_name_override():
    m = raw(1, 1, 1766, 2, 1, 0)
    m["homeTeam"]["shortName"] = "Mineiro"
    assert parse_match(m).home.short == "Atlético-MG"
