from datetime import date

import httpx

from config import get_settings
from utils.http_errors import format_external_api_error
from utils.logging import get_logger

logger = get_logger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred"
PAGE_SIZE = 10000


def _api_key() -> str:
    key = get_settings().fred_api_key
    if not key:
        raise RuntimeError("FRED_API_KEY is not configured")
    return key


def _parse_observations(series_id: str, observations: list[dict]) -> list[dict]:
    rows = []
    for obs in observations:
        val = obs.get("value")
        if val in (None, "."):
            continue
        rows.append({
            "series_id": series_id,
            "obs_date": date.fromisoformat(obs["date"]),
            "value": float(val),
        })
    return rows


async def _fetch_observations_page(
    series_id: str,
    *,
    limit: int,
    offset: int = 0,
    observation_start: date | None = None,
) -> tuple[list[dict], int]:
    url = f"{FRED_BASE}/series/observations"
    params: dict = {
        "series_id": series_id,
        "api_key": _api_key(),
        "file_type": "json",
        "sort_order": "asc",
        "limit": limit,
        "offset": offset,
    }
    if observation_start is not None:
        params["observation_start"] = observation_start.isoformat()

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                format_external_api_error(
                    exc,
                    context=f"FRED observations for {series_id}",
                    secret_values=[_api_key()],
                ),
            ) from exc
        data = resp.json()

    raw = data.get("observations", [])
    return _parse_observations(series_id, raw), len(raw)


async def fetch_all_observations(series_id: str) -> list[dict]:
    all_rows: list[dict] = []
    offset = 0

    while True:
        page, raw_count = await _fetch_observations_page(
            series_id, limit=PAGE_SIZE, offset=offset,
        )
        all_rows.extend(page)
        if raw_count < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    logger.info("fred_fetched_all", series_id=series_id, count=len(all_rows))
    return all_rows


async def fetch_observations_since(series_id: str, start: date) -> list[dict]:
    all_rows: list[dict] = []
    offset = 0

    while True:
        page, raw_count = await _fetch_observations_page(
            series_id,
            limit=PAGE_SIZE,
            offset=offset,
            observation_start=start,
        )
        all_rows.extend(page)
        if raw_count < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    logger.info("fred_fetched_since", series_id=series_id, start=start, count=len(all_rows))
    return all_rows


async def fetch_observations(series_id: str, limit: int = 5000) -> list[dict]:
    """Backward-compatible single-page fetch (oldest rows up to limit)."""
    rows, _ = await _fetch_observations_page(series_id, limit=limit, offset=0)
    return rows
