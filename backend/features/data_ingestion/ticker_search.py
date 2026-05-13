"""Ticker symbol search via Yahoo Finance search API."""
import asyncio
from functools import partial

import requests

from dtos.market_data_dto import TickerSearchResponse, TickerSearchResult
from utils.logging import get_logger

logger = get_logger(__name__)

_YF_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
_YF_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; trading-app/1.0)"}

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


def _fetch_quotes(query: str, limit: int) -> list[dict]:
    params = {
        "q": query,
        "quotesCount": min(limit, 50),
        "newsCount": 0,
        "enableFuzzyQuery": "false",
        "region": "US",
        "lang": "en-US",
    }
    response = requests.get(_YF_SEARCH_URL, params=params, headers=_YF_HEADERS, timeout=10.0)
    response.raise_for_status()
    return response.json().get("quotes") or []


async def search_tickers(query: str, limit: int = 10) -> TickerSearchResponse:
    """Search tickers by name or symbol using Yahoo Finance search API."""
    try:
        loop = asyncio.get_running_loop()
        quotes = await loop.run_in_executor(None, partial(_fetch_quotes, query, limit))
        results = [_parse_quote(q) for q in quotes[:limit]]
        logger.info("ticker_search_completed", query=query, count=len(results))
        return TickerSearchResponse(results=results, count=len(results))
    except Exception as exc:
        logger.error("ticker_search_failed", query=query, error=str(exc))
        return TickerSearchResponse(results=[], count=0)
