from datetime import datetime

import httpx

from dtos.market_data_dto import OHLCVRecord
from features.market_data.bar_aggregate import aggregate_ohlcv_bars
from features.tiingo.common import get_token, parse_timestamp, symbol_to_crypto_ticker
from utils.logging import get_logger

logger = get_logger(__name__)

_CRYPTO_URL = "https://api.tiingo.com/tiingo/crypto/prices"
_SUPPORTED = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}
_CRYPTO_RESAMPLE = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "60min",
    "4h": "60min",
    "1d": "1Day",
}


def _crypto_resample_freq(timeframe: str) -> str:
    if timeframe not in _CRYPTO_RESAMPLE:
        raise ValueError(f"Crypto unsupported timeframe: {timeframe}")
    return _CRYPTO_RESAMPLE[timeframe]


def _extract_rows(payload: list, ticker: str) -> list[dict]:
    for entry in payload:
        if entry.get("ticker", "").lower() == ticker:
            return entry.get("priceData") or []
    return []


def _build_crypto_params(
    ticker: str,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    token: str,
) -> dict[str, str]:
    params: dict[str, str] = {
        "tickers": ticker,
        "resampleFreq": _crypto_resample_freq(timeframe),
        "token": token,
    }
    if start is not None:
        params["startDate"] = start.strftime("%Y-%m-%d")
    if end is not None:
        params["endDate"] = end.strftime("%Y-%m-%d")
    return params


async def fetch_crypto_bars(
    symbol: str,
    instrument_id: int,
    timeframe: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[OHLCVRecord]:
    if timeframe not in _SUPPORTED:
        raise ValueError(f"Crypto unsupported timeframe: {timeframe}")

    if timeframe == "4h":
        hourly = await fetch_crypto_bars(symbol, instrument_id, "1h", start, end)
        return aggregate_ohlcv_bars(hourly, "4h")

    ticker = symbol_to_crypto_ticker(symbol)
    token = get_token()
    params = _build_crypto_params(ticker, timeframe, start, end, token)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(_CRYPTO_URL, params=params)
        resp.raise_for_status()
        rows = _extract_rows(resp.json(), ticker)

    records = [
        OHLCVRecord(
            time=parse_timestamp(row["date"]),
            instrument_id=instrument_id,
            timeframe=timeframe,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row.get("volume") or 0),
            source="tiingo_crypto",
        )
        for row in rows
    ]
    logger.info("crypto_fetched", symbol=symbol, timeframe=timeframe, count=len(records))
    return records
