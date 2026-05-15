"""Tiingo IEX provider — intraday historical OHLCV via the Tiingo REST API."""
from datetime import datetime, timezone
from typing import Optional

import httpx

from config import get_settings
from dtos.market_data_dto import FundamentalRecord, OHLCVRecord
from utils.logging import get_logger

from .base_provider import DataProvider

logger = get_logger(__name__)

_TIINGO_IEX_BASE = "https://api.tiingo.com/iex"
_SUPPORTED_TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h"}
_RESAMPLE_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "60min",
}
_REQUEST_TIMEOUT = 30.0


def _build_params(symbol: str, timeframe: str, start: datetime, end: datetime, token: str) -> dict:
    """Build query parameters for the Tiingo IEX historical prices endpoint."""
    return {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "resampleFreq": _RESAMPLE_MAP[timeframe],
        "columns": "open,high,low,close,volume",
        "token": token,
    }


def _parse_timestamp(raw: str) -> datetime:
    """Parse Tiingo ISO timestamp to timezone-aware datetime."""
    ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _row_to_record(row: dict, asset_id: int, timeframe: str) -> OHLCVRecord:
    """Convert a single Tiingo IEX response row to an OHLCVRecord."""
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


async def _fetch_tiingo_bars(
    symbol: str,
    params: dict,
) -> list[dict]:
    """Perform the async HTTP request to Tiingo IEX historical prices endpoint."""
    url = f"{_TIINGO_IEX_BASE}/{symbol.upper()}/prices"
    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


class TiingoProvider(DataProvider):
    """Tiingo IEX wrapper — provides intraday historical OHLCV bars."""

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
    ) -> list[OHLCVRecord]:
        if timeframe not in _SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Tiingo IEX does not support timeframe '{timeframe}'. "
                f"Supported: {sorted(_SUPPORTED_TIMEFRAMES)}"
            )

        token = get_settings().tiingo_api_key
        if not token:
            raise RuntimeError("TIINGO_API_KEY is not configured")

        params = _build_params(symbol, timeframe, start, end, token)

        try:
            rows = await _fetch_tiingo_bars(symbol, params)
        except httpx.HTTPStatusError as exc:
            logger.error(
                "tiingo_http_error",
                symbol=symbol,
                status=exc.response.status_code,
                body=exc.response.text[:200],
            )
            raise

        if not rows:
            logger.info("tiingo_no_data", symbol=symbol, timeframe=timeframe)
            return []

        records = [_row_to_record(row, asset_id or 0, timeframe) for row in rows]
        logger.info("tiingo_ohlcv_fetched", symbol=symbol, timeframe=timeframe, count=len(records))
        return records

    async def fetch_fundamentals(
        self,
        symbol: str,
        asset_id: Optional[int] = None,
    ) -> list[FundamentalRecord]:
        """Tiingo IEX does not provide fundamentals; returns empty list."""
        return []
