"""Cliente HTTP mínimo para a API football-data.org (v4)."""
from __future__ import annotations

import time

import httpx

from .config import Settings
from .models import Match, parse_match


class ApiError(RuntimeError):
    pass


def fetch_matches(settings: Settings, retries: int = 3) -> list[Match]:
    """Busca todas as partidas da temporada (jogadas e a jogar) em uma única chamada."""
    if not settings.token:
        raise ApiError("Defina FOOTBALL_DATA_TOKEN (variável de ambiente ou secret do GitHub).")

    url = f"{settings.api_base}/competitions/{settings.competition}/matches"
    headers = {"X-Auth-Token": settings.token, "Accept": "application/json"}
    params = {"season": settings.season}

    last_exc: Exception | None = None
    with httpx.Client(timeout=settings.timeout_s, headers=headers) as client:
        for attempt in range(1, retries + 1):
            try:
                resp = client.get(url, params=params)
                if resp.status_code == 429:  # limite do plano gratuito (10 req/min)
                    wait = int(resp.headers.get("X-RequestCounter-Reset", "60"))
                    time.sleep(min(wait, 65))
                    continue
                resp.raise_for_status()
                payload = resp.json()
                return [parse_match(m) for m in payload.get("matches", [])]
            except (httpx.HTTPError, ValueError) as exc:
                last_exc = exc
                time.sleep(2 ** attempt)
    raise ApiError(f"Falha ao buscar partidas: {last_exc}")
