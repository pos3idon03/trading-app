"""Ticker symbol search via Polygon reference API."""
from config import get_settings
from dtos.market_data_dto import TickerSearchResponse, TickerSearchResult
from utils.api_client import fetch_json
from utils.logging import get_logger

logger = get_logger(__name__)

POLYGON_BASE = "https://api.polygon.io"
_POLYGON_TYPE_MAP = {
    "CS": "stock",
    "ETF": "etf",
    "ADRC": "stock",
    "ADRP": "stock",
    "ADRR": "stock",
    "UNIT": "other",
    "RIGHT": "other",
    "PFD": "stock",
    "FUND": "etf",
    "SP": "other",
    "WARRANT": "other",
}


def _map_asset_type(polygon_type: str | None) -> str:
    return _POLYGON_TYPE_MAP.get(polygon_type or "", "stock")


def _parse_result(item: dict) -> TickerSearchResult:
    return TickerSearchResult(
        symbol=item.get("ticker", ""),
        name=item.get("name", ""),
        asset_type=_map_asset_type(item.get("type")),
        exchange=item.get("primary_exchange"),
    )


async def search_tickers(query: str, limit: int = 10) -> TickerSearchResponse:
    """Search tickers by name or symbol using Polygon reference API."""
    api_key = get_settings().polygon_api_key
    url = f"{POLYGON_BASE}/v3/reference/tickers"
    params = {
        "search": query,
        "active": "true",
        "market": "stocks",
        "limit": min(limit, 50),
        "apiKey": api_key,
    }

    try:
        data = await fetch_json(url, params=params)
        items = data.get("results") or []
        results = [_parse_result(item) for item in items]
        logger.info("ticker_search_completed", query=query, count=len(results))
        return TickerSearchResponse(results=results, count=len(results))
    except Exception as exc:
        logger.error("ticker_search_failed", query=query, error=str(exc))
        return TickerSearchResponse(results=[], count=0)
