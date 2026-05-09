"""FRED (Federal Reserve Economic Data) tool.

Fetches key macroeconomic series from the St. Louis Fed FRED API.
Requires FRED_API_KEY environment variable.
"""
from typing import Optional

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import get_settings
from utils.logging import get_logger

logger = get_logger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred"

SERIES_CATALOG = {
    "DFF": "Federal Funds Rate (overnight, daily)",
    "DGS10": "10-Year Treasury Yield (%)",
    "DGS2": "2-Year Treasury Yield (%)",
    "CPIAUCSL": "CPI All Urban Consumers (monthly, seasonally adjusted)",
    "UNRATE": "Unemployment Rate (%)",
    "GDPC1": "Real GDP (quarterly, seasonally adjusted annual rate)",
    "DEXUSEU": "USD/EUR Exchange Rate",
    "VIXCLS": "CBOE Volatility Index (VIX, daily)",
}


class FredInput(BaseModel):
    series_ids: list[str] = Field(
        default=["DFF", "DGS10", "CPIAUCSL", "UNRATE"],
        description="List of FRED series IDs to fetch. Common: DFF, DGS10, CPIAUCSL, UNRATE, GDPC1, VIXCLS.",
    )
    observation_count: int = Field(default=5, ge=1, le=20, description="Number of most recent observations to return per series.")


class FredTool(BaseTool):
    name: str = "fred_macro_data"
    description: str = (
        "Fetches macroeconomic data from FRED (Federal Reserve). "
        "Returns recent observations for series like: DFF (fed funds rate), DGS10 (10Y yield), "
        "CPIAUCSL (CPI inflation), UNRATE (unemployment), GDPC1 (GDP), VIXCLS (VIX). "
        "Use this to assess the current macro environment."
    )
    args_schema: type[BaseModel] = FredInput

    def _run(self, series_ids: list[str], observation_count: int = 5) -> str:
        api_key = get_settings().fred_api_key
        if not api_key:
            return "FRED_API_KEY is not configured. Cannot fetch macro data."
        results = []
        for sid in series_ids:
            data = _fetch_series(sid, api_key, observation_count)
            results.append(_format_series(sid, data))
        return "\n\n".join(results)


def _fetch_series(series_id: str, api_key: str, count: int) -> Optional[dict]:
    """Fetch a single FRED series with its most recent observations."""
    url = f"{FRED_BASE_URL}/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": count,
    }
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("fred_fetch_error", series=series_id, error=str(exc))
        return None


def _format_series(series_id: str, data: Optional[dict]) -> str:
    label = SERIES_CATALOG.get(series_id, series_id)
    if data is None:
        return f"{label} ({series_id}): [fetch failed]"

    obs = data.get("observations", [])
    if not obs:
        return f"{label} ({series_id}): [no data]"

    lines = [f"{label} ({series_id}):"]
    for o in obs:
        value = o.get("value", ".")
        date = o.get("date", "?")
        display = "N/A" if value == "." else value
        lines.append(f"  {date}: {display}")
    return "\n".join(lines)
