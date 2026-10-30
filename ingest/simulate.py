"""Simulação Monte Carlo do restante do campeonato (vetorizada em NumPy)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .model import Strengths
from .models import Match, Row


@dataclass(frozen=True)
class SimResult:
    team_ids: list[int]
    position_probs: np.ndarray  # [time, posição] — linhas somam 1
    expected_points: np.ndarray
    n_sims: int


def simulate(table: list[Row], pending: list[Match], strengths: Strengths,
             n_sims: int, seed: int | None = None) -> SimResult:
    rng = np.random.default_rng(seed)
    team_ids = [r.team.id for r in table]
    idx = {tid: i for i, tid in enumerate(team_ids)}
    n = len(team_ids)

    pts = np.tile(np.array([r.pts for r in table], dtype=np.int32), (n_sims, 1))
    wins = np.tile(np.array([r.v for r in table], dtype=np.int32), (n_sims, 1))
    gd = np.tile(np.array([r.sg for r in table], dtype=np.int32), (n_sims, 1))
    gf = np.tile(np.array([r.gp for r in table], dtype=np.int32), (n_sims, 1))

    for m in pending:
        h, a = idx[m.home.id], idx[m.away.id]
        lam_h, lam_a = strengths.rates(m.home.id, m.away.id)
        gh = rng.poisson(lam_h, n_sims).astype(np.int32)
        ga = rng.poisson(lam_a, n_sims).astype(np.int32)
        home_win, draw, away_win = gh > ga, gh == ga, gh < ga
        pts[:, h] += 3 * home_win + draw
        pts[:, a] += 3 * away_win + draw
        wins[:, h] += home_win
        wins[:, a] += away_win
        gd[:, h] += gh - ga
        gd[:, a] += ga - gh
        gf[:, h] += gh
        gf[:, a] += ga

    # Critérios: pontos > vitórias > saldo > gols pró > sorteio (ruído uniforme)
    key = (pts.astype(np.float64) * 1e9 + wins * 1e6 + (gd + 500) * 1e3 + gf
           + rng.random((n_sims, n)))
    order = np.argsort(-key, axis=1)               # order[s, p] = time na posição p
    positions = np.empty_like(order)
    positions[np.arange(n_sims)[:, None], order] = np.arange(n)  # positions[s, t] = posição do time t

    counts = np.zeros((n, n), dtype=np.int64)
    for t in range(n):
        counts[t] = np.bincount(positions[:, t], minlength=n)

    return SimResult(team_ids, counts / n_sims, pts.mean(axis=0), n_sims)
