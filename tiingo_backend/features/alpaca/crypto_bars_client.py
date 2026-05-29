from datetime import datetime, timezone

import httpx

from config import get_settings
from dtos.market_data_dto import OHLCVRecord
from features.execution.alpaca_symbols import to_alpaca_symbol
from features.market_data.bar_aggregate import aggregate_ohlcv_bars
from utils.logging import get_logger

logger = get_logger(__name__)

_BARS_PATH = "/v1beta3/crypto/us/bars"
_SUPPORTED = frozenset({"1m", "5m", "15m", "30m", "1h", "4h", "1d"})
_ALPACA_TIMEFRAME = {
    "1m": "1Min",
    "5m": "5Min",
    "15m": "15Min",
    "30m": "30Min",
    "1h": "1Hour",
    "1d": "1Day",
}


def _headers() -> dict[str, str]:
    settings = get_settings()
    if not settings.alpaca_configured:
        raise RuntimeError("Alpaca API credentials are not configured")
    return {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
    }


def _data_base_url() -> str:
    return get_settings().alpaca_data_base_url.rstrip("/")


def _alpaca_timeframe(timeframe: str) -> str:
    if timeframe not in _ALPACA_TIMEFRAME:
        raise ValueError(f"Alpaca crypto unsupported timeframe: {timeframe}")
    return _ALPACA_TIMEFRAME[timeframe]


def _parse_bar_time(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_param(value: datetime) -> str:
    utc = value.astimezone(timezone.utc).replace(microsecond=0)
    return utc.isoformat().replace("+00:00", "Z")


async def fetch_crypto_bars(
    symbol: str,
    instrument_id: int,
    timeframe: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[OHLCVRecord]:
    if timeframe not in _SUPPORTED:
        raise ValueError(f"Alpaca crypto unsupported timeframe: {timeframe}")

    if timeframe == "4h":
        hourly = await fetch_crypto_bars(symbol, instrument_id, "1h", start, end)
        return aggregate_ohlcv_bars(hourly, "4h")

    alpaca_symbol = to_alpaca_symbol(symbol, "crypto")
    base_params: dict[str, str] = {
        "symbols": alpaca_symbol,
        "timeframe": _alpaca_timeframe(timeframe),
        "limit": "10000",
    }
    if start is not None:
        base_params["start"] = _iso_param(start)
    if end is not None:
        base_params["end"] = _iso_param(end)

    url = f"{_data_base_url()}{_BARS_PATH}"
    rows: list[dict] = []
    page_token: str | None = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            params = dict(base_params)
            if page_token:
                params["page_token"] = page_token
            response = await client.get(url, headers=_headers(), params=params)
            response.raise_for_status()
            payload = response.json()
            rows.extend((payload.get("bars") or {}).get(alpaca_symbol) or [])
            page_token = payload.get("next_page_token")
            if not page_token:
                break

    records = [
        OHLCVRecord(
            time=_parse_bar_time(row["t"]),
            instrument_id=instrument_id,
            timeframe=timeframe,
            open=float(row["o"]),
            high=float(row["h"]),
            low=float(row["l"]),
            close=float(row["c"]),
            volume=int(row.get("v") or 0),
            vwap=float(row["vw"]) if row.get("vw") is not None else None,
            trade_count=int(row["n"]) if row.get("n") is not None else None,
            source="alpaca_crypto",
        )
        for row in rows
    ]
    logger.info(
        "alpaca_crypto_fetched",
        symbol=symbol,
        timeframe=timeframe,
        count=len(records),
    )
    return records
