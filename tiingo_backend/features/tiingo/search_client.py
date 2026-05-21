"""Tiingo Utilities Search — ticker lookup by name or symbol."""
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from dtos.market_data_dto import TickerSearchResponseDTO, TickerSearchResultDTO
from features.tiingo.common import get_token
from utils.logging import get_logger
from utils.rate_limiter import check_and_increment

logger = get_logger(__name__)

_SEARCH_URL = "https://api.tiingo.com/tiingo/utilities/search"

_ASSET_TYPE_MAP = {
    "stock": "stock",
    "etf": "etf",
    "mutual fund": "mutual_fund",
    "mutualfund": "mutual_fund",
    "crypto": "crypto",
    "cryptocurrency": "crypto",
    "forex": "forex",
}


def map_asset_type(raw: str | None) -> str:
    if not raw:
        return "stock"
    key = raw.strip().lower()
    return _ASSET_TYPE_MAP.get(key, "stock")


def _parse_item(item: dict) -> TickerSearchResultDTO | None:
    ticker = (item.get("ticker") or "").strip()
    if not ticker:
        return None
    name = (item.get("name") or ticker).strip()
    return TickerSearchResultDTO(
        symbol=ticker.upper(),
        name=name,
        asset_type=map_asset_type(item.get("assetType")),
        exchange=item.get("exchange"),
        tiingo_ticker=ticker,
    )


async def search_tickers(
    query: str,
    limit: int = 10,
    session: AsyncSession | None = None,
) -> TickerSearchResponseDTO:
    token = get_token()
    params = {"query": query, "token": token}

    try:
        if session is not None:
            await check_and_increment(session)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_SEARCH_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        logger.error("tiingo_search_failed", query=query, error=str(exc))
        return TickerSearchResponseDTO(results=[], count=0)

    items = payload if isinstance(payload, list) else []
    results: list[TickerSearchResultDTO] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        parsed = _parse_item(item)
        if parsed:
            results.append(parsed)

    logger.info("tiingo_search_done", query=query, count=len(results))
    return TickerSearchResponseDTO(results=results, count=len(results))
