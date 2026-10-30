"""Tipos de domínio e parsing do payload da API."""
from __future__ import annotations

from dataclasses import dataclass, field

FINISHED = {"FINISHED", "AWARDED"}
DISCARDED = {"CANCELLED"}
# shortName da API que fica ambíguo ou longo na página
SHORT_NAMES = {1766: "Atlético-MG", 1768: "Athletico-PR", 4287: "Remo"}


@dataclass(frozen=True)
class Team:
    id: int
    name: str
    short: str
    crest: str | None = None


@dataclass(frozen=True)
class Match:
    id: int
    matchday: int | None
    utc_date: str
    status: str
    home: Team
    away: Team
    home_goals: int | None = None
    away_goals: int | None = None

    @property
    def played(self) -> bool:
        return self.status in FINISHED and self.home_goals is not None and self.away_goals is not None

    @property
    def pending(self) -> bool:
        return not self.played and self.status not in DISCARDED


@dataclass
class Row:
    team: Team
    j: int = 0
    v: int = 0
    e: int = 0
    d: int = 0
    gp: int = 0
    gc: int = 0
    form: list[str] = field(default_factory=list)  # últimos resultados, mais recente por último

    @property
    def pts(self) -> int:
        return 3 * self.v + self.e

    @property
    def sg(self) -> int:
        return self.gp - self.gc


def _team(raw: dict) -> Team:
    return Team(
        id=int(raw["id"]),
        name=raw.get("name") or raw.get("shortName") or str(raw["id"]),
        short=SHORT_NAMES.get(int(raw["id"])) or raw.get("shortName") or raw.get("name") or str(raw["id"]),
        crest=raw.get("crest"),
    )


def parse_match(raw: dict) -> Match:
    full = (raw.get("score") or {}).get("fullTime") or {}
    return Match(
        id=int(raw["id"]),
        matchday=raw.get("matchday"),
        utc_date=raw.get("utcDate", ""),
        status=raw.get("status", "SCHEDULED"),
        home=_team(raw["homeTeam"]),
        away=_team(raw["awayTeam"]),
        home_goals=full.get("home"),
        away_goals=full.get("away"),
    )
