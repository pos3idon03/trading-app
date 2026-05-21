from datetime import date

import httpx

from config import get_settings
from utils.logging import get_logger

logger = get_logger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred"


def _api_key() -> str:
    key = get_settings().fred_api_key
    if not key:
        raise RuntimeError("FRED_API_KEY is not configured")
    return key


async def fetch_observations(series_id: str, limit: int = 5000) -> list[dict]:
    url = f"{FRED_BASE}/series/observations"
    params = {
        "series_id": series_id,
        "api_key": _api_key(),
        "file_type": "json",
        "sort_order": "asc",
        "limit": limit,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    rows = []
    for obs in data.get("observations", []):
        val = obs.get("value")
        if val in (None, "."):
            continue
        rows.append({
            "series_id": series_id,
            "obs_date": date.fromisoformat(obs["date"]),
            "value": float(val),
        })
    logger.info("fred_fetched", series_id=series_id, count=len(rows))
    return rows
