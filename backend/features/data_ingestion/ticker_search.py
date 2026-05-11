"""Ticker symbol search via yfinance."""
import asyncio
from functools import partial

import yfinance as yf

from dtos.market_data_dto import TickerSearchResponse, TickerSearchResult
from utils.logging import get_logger

logger = get_logger(__name__)

_QUOTE_TYPE_MAP = {
    "EQUITY": "stock",
    "ETF": "etf",
    "MUTUALFUND": "etf",
    "CRYPTOCURRENCY": "crypto",
    "CURRENCY": "forex",
    "INDEX": "index",
    "FUTURE": "future",
    "OPTION": "option",
}


def _map_asset_type(quote_type: str | None) -> str:
    return _QUOTE_TYPE_MAP.get((quote_type or "").upper(), "stock")


def _parse_quote(item: dict) -> TickerSearchResult:
    name = item.get("longname") or item.get("shortname") or ""
    return TickerSearchResult(
        symbol=item.get("symbol", ""),
        name=name,
        asset_type=_map_asset_type(item.get("typeDisp") or item.get("quoteType")),
        exchange=item.get("exchange"),
    )


def _run_yfinance_search(query: str) -> list[dict]:
    return yf.Search(query).quotes


async def search_tickers(query: str, limit: int = 10) -> TickerSearchResponse:
    """Search tickers by name or symbol using yfinance."""
    try:
        loop = asyncio.get_running_loop()
        quotes = await loop.run_in_executor(None, partial(_run_yfinance_search, query))
        results = [_parse_quote(q) for q in (quotes or [])[:limit]]
        logger.info("ticker_search_completed", query=query, count=len(results))
        return TickerSearchResponse(results=results, count=len(results))
    except Exception as exc:
        logger.error("ticker_search_failed", query=query, error=str(exc))
        return TickerSearchResponse(results=[], count=0)
