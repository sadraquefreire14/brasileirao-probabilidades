"""Modelo de gols de Poisson com forças de ataque/defesa por time.

λ_mandante  = μ_casa  · ataque[mandante]  · defesa[visitante]
λ_visitante = μ_fora  · ataque[visitante] · defesa[mandante]

As forças são estimadas por ajuste proporcional iterativo (equivalente ao
máximo da verossimilhança de Poisson), com:
  * peso exponencial por rodada (jogos recentes valem mais);
  * encolhimento em direção à média da liga (evita extremos com poucos jogos).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .models import Match

MAX_GOALS = 10


@dataclass(frozen=True)
class Strengths:
    team_ids: list[int]
    attack: np.ndarray
    defense: np.ndarray
    mu_home: float
    mu_away: float

    def index(self) -> dict[int, int]:
        return {tid: i for i, tid in enumerate(self.team_ids)}

    def rates(self, home_id: int, away_id: int) -> tuple[float, float]:
        idx = self.index()
        h, a = idx[home_id], idx[away_id]
        return (
            self.mu_home * self.attack[h] * self.defense[a],
            self.mu_away * self.attack[a] * self.defense[h],
        )


def fit(matches: list[Match], team_ids: list[int], half_life: float, prior_matches: float,
        iterations: int = 100) -> Strengths:
    idx = {tid: i for i, tid in enumerate(team_ids)}
    played = [m for m in matches if m.played]
    n = len(team_ids)

    if not played:
        ones = np.ones(n)
        return Strengths(team_ids, ones, ones.copy(), 1.4, 1.1)

    H = np.array([idx[m.home.id] for m in played])
    A = np.array([idx[m.away.id] for m in played])
    hg = np.array([m.home_goals for m in played], dtype=float)
    ag = np.array([m.away_goals for m in played], dtype=float)
    md = np.array([m.matchday or 0 for m in played], dtype=float)
    w = 0.5 ** ((md.max() - md) / half_life)

    mu_home = float((w * hg).sum() / w.sum())
    mu_away = float((w * ag).sum() / w.sum())
    k = prior_matches * (mu_home + mu_away) / 2  # pseudo-gols da média da liga

    att = np.ones(n)
    dfn = np.ones(n)
    for _ in range(iterations):
        # ataque: gols marcados / gols esperados com ataque = 1
        scored = np.bincount(H, w * hg, n) + np.bincount(A, w * ag, n)
        exp_s = np.bincount(H, w * mu_home * dfn[A], n) + np.bincount(A, w * mu_away * dfn[H], n)
        att = (scored + k) / (exp_s + k)
        att /= att.mean()
        # defesa: gols sofridos / gols esperados com defesa = 1
        conceded = np.bincount(H, w * ag, n) + np.bincount(A, w * hg, n)
        exp_c = np.bincount(H, w * mu_away * att[A], n) + np.bincount(A, w * mu_home * att[H], n)
        dfn = (conceded + k) / (exp_c + k)
        dfn /= dfn.mean()

    return Strengths(team_ids, att, dfn, mu_home, mu_away)


def outcome_probs(lam_h: float, lam_a: float) -> tuple[float, float, float]:
    """Probabilidades exatas (truncadas) de vitória do mandante, empate e vitória do visitante."""
    g = np.arange(MAX_GOALS + 1)
    fact = np.cumprod(np.r_[1, g[1:]]).astype(float)
    ph = np.exp(-lam_h) * lam_h ** g / fact
    pa = np.exp(-lam_a) * lam_a ** g / fact
    grid = np.outer(ph, pa)
    total = grid.sum()
    return (
        float(np.tril(grid, -1).sum() / total),
        float(np.trace(grid) / total),
        float(np.triu(grid, 1).sum() / total),
    )
