import httpx

from features.tiingo.common import get_token
from utils.logging import get_logger

logger = get_logger(__name__)

_DISTRIBUTIONS_BASE = "https://api.tiingo.com/tiingo/corporate-actions"


def _parse_trailing_yield(raw: object) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return round(value * 100.0, 2)


def _latest_trailing_yield(rows: list[dict]) -> float | None:
    if not rows:
        return None
    latest = max(rows, key=lambda row: row.get("date") or "")
    return _parse_trailing_yield(latest.get("trailingDiv1Y"))


async def fetch_distribution_yield(ticker: str) -> float | None:
    token = get_token()
    url = f"{_DISTRIBUTIONS_BASE}/{ticker.upper()}/distribution-yield"
    params = {"columns": "trailingDiv1Y", "token": token}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        payload = resp.json()

    if not isinstance(payload, list):
        return None

    yield_pct = _latest_trailing_yield(payload)
    logger.info("distribution_yield_fetched", ticker=ticker.upper(), yield_pct=yield_pct)
    return yield_pct
