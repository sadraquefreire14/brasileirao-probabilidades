"""Configuração central da ingestão e da simulação.

Valores de regulamento (vagas e rebaixamento) ficam aqui para serem
ajustados a cada temporada sem tocar no código.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "src" / "data"
SNAPSHOT_FILE = DATA_DIR / "brasileirao.json"
HISTORY_FILE = DATA_DIR / "history.json"


@dataclass(frozen=True)
class Settings:
    api_base: str = "https://api.football-data.org/v4"
    competition: str = "BSA"  # Campeonato Brasileiro Série A
    season: int = int(os.getenv("SEASON", "2026"))
    token: str | None = os.getenv("FOOTBALL_DATA_TOKEN")
    timeout_s: float = 20.0

    # Regulamento
    n_teams: int = 20
    libertadores_direct: int = 5  # 1º ao 5º: vaga direta (6º/7º dependem da Copa do Brasil)
    relegated: int = 4            # 17º ao 20º

    # Modelo
    n_sims: int = int(os.getenv("N_SIMS", "20000"))
    seed: int | None = None
    half_life_matchdays: float = 12.0  # peso de jogos antigos cai pela metade a cada 12 rodadas
    prior_matches: float = 6.0          # encolhimento das forças em direção à média da liga


SETTINGS = Settings()
