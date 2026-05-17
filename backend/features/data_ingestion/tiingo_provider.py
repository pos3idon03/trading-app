"""Tiingo provider — intraday historical OHLCV via IEX (stocks) and Crypto APIs."""
from datetime import datetime, timezone
from typing import Optional

import httpx

from config import get_settings
from dtos.market_data_dto import FundamentalRecord, OHLCVRecord
from utils.logging import get_logger

from .base_provider import DataProvider

logger = get_logger(__name__)

_TIINGO_IEX_BASE = "https://api.tiingo.com/iex"
_TIINGO_CRYPTO_PRICES = "https://api.tiingo.com/tiingo/crypto/prices"
_SUPPORTED_TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h"}
_RESAMPLE_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "60min",
}
_REQUEST_TIMEOUT = 30.0


def symbol_to_tiingo_crypto_ticker(symbol: str) -> str:
    """Map app symbol (e.g. BTC-USD) to Tiingo crypto ticker (e.g. btcusd).

    Only call when asset_type is crypto so hyphenated equities (e.g. BRK-B) are not misrouted.
    """
    parts = symbol.upper().split("-", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Crypto symbol '{symbol}' must be BASE-QUOTE (e.g. BTC-USD)"
        )
    return f"{parts[0]}{parts[1]}".lower()


def _build_iex_params(
    timeframe: str, start: datetime, end: datetime, token: str
) -> dict:
    """Build query parameters for the Tiingo IEX historical prices endpoint."""
    return {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "resampleFreq": _RESAMPLE_MAP[timeframe],
        "columns": "open,high,low,close,volume",
        "token": token,
    }


def _build_crypto_params(
    tiingo_ticker: str, timeframe: str, start: datetime, end: datetime, token: str
) -> dict:
    """Build query parameters for the Tiingo crypto historical prices endpoint."""
    return {
        "tickers": tiingo_ticker,
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "resampleFreq": _RESAMPLE_MAP[timeframe],
        "token": token,
    }


def _parse_timestamp(raw: str) -> datetime:
    """Parse Tiingo ISO timestamp to timezone-aware datetime."""
    ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _row_to_record(row: dict, asset_id: int, timeframe: str) -> OHLCVRecord:
    """Convert a single Tiingo OHLCV row to an OHLCVRecord."""
    return OHLCVRecord(
        time=_parse_timestamp(row["date"]),
        asset_id=asset_id,
        timeframe=timeframe,
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=int(row.get("volume") or 0),
        source="tiingo",
    )


def _crypto_response_to_rows(payload: list, tiingo_ticker: str) -> list[dict]:
    """Extract priceData rows from Tiingo crypto prices response."""
    for entry in payload:
        if entry.get("ticker", "").lower() == tiingo_ticker:
            return entry.get("priceData") or []
    return []


async def _fetch_tiingo_iex_bars(symbol: str, params: dict) -> list[dict]:
    """Perform the async HTTP request to Tiingo IEX historical prices endpoint."""
    url = f"{_TIINGO_IEX_BASE}/{symbol.upper()}/prices"
    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def _fetch_tiingo_crypto_bars(params: dict) -> list[dict]:
    """Perform the async HTTP request to Tiingo crypto historical prices endpoint."""
    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        response = await client.get(_TIINGO_CRYPTO_PRICES, params=params)
        response.raise_for_status()
        payload = response.json()
    return _crypto_response_to_rows(payload, params["tickers"].lower())


class TiingoProvider(DataProvider):
    """Tiingo wrapper — intraday OHLCV for stocks (IEX) and crypto."""

    @property
    def name(self) -> str:
        return "tiingo"

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        asset_id: Optional[int] = None,
        asset_type: Optional[str] = None,
    ) -> list[OHLCVRecord]:
        if timeframe not in _SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Tiingo does not support timeframe '{timeframe}'. "
                f"Supported: {sorted(_SUPPORTED_TIMEFRAMES)}"
            )

        token = get_settings().tiingo_api_key
        if not token:
            raise RuntimeError("TIINGO_API_KEY is not configured")

        is_crypto = asset_type == "crypto"
        try:
            if is_crypto:
                tiingo_ticker = symbol_to_tiingo_crypto_ticker(symbol)
                params = _build_crypto_params(
                    tiingo_ticker, timeframe, start, end, token
                )
                rows = await _fetch_tiingo_crypto_bars(params)
            else:
                params = _build_iex_params(timeframe, start, end, token)
                rows = await _fetch_tiingo_iex_bars(symbol, params)
        except httpx.HTTPStatusError as exc:
            logger.error(
                "tiingo_http_error",
                symbol=symbol,
                asset_type=asset_type or "stock",
                status=exc.response.status_code,
                body=exc.response.text[:200],
            )
            raise

        if not rows:
            logger.info(
                "tiingo_no_data",
                symbol=symbol,
                timeframe=timeframe,
                asset_type=asset_type or "stock",
            )
            return []

        records = [_row_to_record(row, asset_id or 0, timeframe) for row in rows]
        logger.info(
            "tiingo_ohlcv_fetched",
            symbol=symbol,
            timeframe=timeframe,
            asset_type=asset_type or "stock",
            count=len(records),
        )
        return records

    async def fetch_fundamentals(
        self,
        symbol: str,
        asset_id: Optional[int] = None,
    ) -> list[FundamentalRecord]:
        """Tiingo does not provide fundamentals via this provider; returns empty list."""
        return []
