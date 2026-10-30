"""Classificação calculada a partir das partidas.

Critérios de desempate do Brasileirão aplicados aqui: pontos, vitórias,
saldo de gols e gols pró. Confronto direto e cartões raramente decidem e
ficam de fora (documentado no README).
"""
from __future__ import annotations

from collections.abc import Iterable

from .models import Match, Row, Team


def sort_key(row: Row) -> tuple:
    return (-row.pts, -row.v, -row.sg, -row.gp, row.team.short)


def build_table(matches: Iterable[Match]) -> list[Row]:
    rows: dict[int, Row] = {}

    def row(team: Team) -> Row:
        return rows.setdefault(team.id, Row(team=team))

    for m in sorted(matches, key=lambda m: m.utc_date):
        h, a = row(m.home), row(m.away)  # registra também times sem jogos disputados
        if not m.played:
            continue
        hg, ag = m.home_goals, m.away_goals
        h.j += 1; a.j += 1
        h.gp += hg; h.gc += ag
        a.gp += ag; a.gc += hg
        if hg > ag:
            h.v += 1; a.d += 1; h.form.append("V"); a.form.append("D")
        elif hg < ag:
            a.v += 1; h.d += 1; a.form.append("V"); h.form.append("D")
        else:
            h.e += 1; a.e += 1; h.form.append("E"); a.form.append("E")

    return sorted(rows.values(), key=sort_key)
