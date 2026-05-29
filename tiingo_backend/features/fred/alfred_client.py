from datetime import date

import httpx

from config import get_settings
from features.fred.fred_client import FRED_BASE, PAGE_SIZE, _api_key
from utils.http_errors import format_external_api_error, redact_secrets
from utils.logging import get_logger

logger = get_logger(__name__)

_ALFRED_REALTIME_START = date(1776, 7, 4)
_ALFRED_REALTIME_END = date(9999, 12, 31)


def _parse_vintage_observations(series_id: str, observations: list[dict]) -> list[dict]:
    rows = []
    for obs in observations:
        val = obs.get("value")
        if val in (None, "."):
            continue
        release_raw = obs.get("realtime_start")
        if not release_raw:
            continue
        rows.append({
            "series_id": series_id,
            "obs_date": date.fromisoformat(obs["date"]),
            "value": float(val),
            "release_date": date.fromisoformat(release_raw),
        })
    return rows


def _collapse_initial_releases(vintage_rows: list[dict]) -> list[dict]:
    earliest: dict[tuple[str, date], dict] = {}
    for row in vintage_rows:
        key = (row["series_id"], row["obs_date"])
        existing = earliest.get(key)
        if existing is None or row["release_date"] < existing["release_date"]:
            earliest[key] = row
    return sorted(earliest.values(), key=lambda item: item["obs_date"])


async def _fetch_vintage_page(
    series_id: str,
    *,
    offset: int,
) -> tuple[list[dict], int]:
    params: dict = {
        "series_id": series_id,
        "api_key": _api_key(),
        "file_type": "json",
        "sort_order": "asc",
        "limit": PAGE_SIZE,
        "offset": offset,
        "output_type": 1,
        "realtime_start": _ALFRED_REALTIME_START.isoformat(),
        "realtime_end": _ALFRED_REALTIME_END.isoformat(),
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{FRED_BASE}/series/observations", params=params)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                format_external_api_error(
                    exc,
                    context=f"FRED ALFRED observations for {series_id}",
                    secret_values=[_api_key()],
                ),
            ) from exc
        data = resp.json()

    raw = data.get("observations", [])
    return _parse_vintage_observations(series_id, raw), len(raw)


async def fetch_initial_release_observations(series_id: str) -> list[dict]:
    if not get_settings().fred_api_key:
        raise RuntimeError("FRED_API_KEY is not configured")

    all_rows: list[dict] = []
    offset = 0
    while True:
        page, raw_count = await _fetch_vintage_page(series_id, offset=offset)
        all_rows.extend(page)
        if raw_count < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    collapsed = _collapse_initial_releases(all_rows)
    logger.info(
        "alfred_initial_release_fetched",
        series_id=series_id,
        vintage_rows=len(all_rows),
        unique_obs=len(collapsed),
    )
    return collapsed
