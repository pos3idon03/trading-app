from datetime import datetime

import httpx

from dtos.market_data_dto import OHLCVRecord
from features.market_data.bar_aggregate import aggregate_ohlcv_bars
from features.tiingo.common import get_token, parse_timestamp, resample_freq, symbol_to_crypto_ticker
from utils.logging import get_logger

logger = get_logger(__name__)

_CRYPTO_URL = "https://api.tiingo.com/tiingo/crypto/prices"
_SUPPORTED = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}


def _extract_rows(payload: list, ticker: str) -> list[dict]:
    for entry in payload:
        if entry.get("ticker", "").lower() == ticker:
            return entry.get("priceData") or []
    return []


async def fetch_crypto_bars(
    symbol: str,
    instrument_id: int,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> list[OHLCVRecord]:
    if timeframe not in _SUPPORTED:
        raise ValueError(f"Crypto unsupported timeframe: {timeframe}")

    if timeframe == "4h":
        hourly = await fetch_crypto_bars(symbol, instrument_id, "1h", start, end)
        return aggregate_ohlcv_bars(hourly, "4h")

    fetch_timeframe = timeframe
    ticker = symbol_to_crypto_ticker(symbol)
    token = get_token()
    params = {
        "tickers": ticker,
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "resampleFreq": resample_freq(fetch_timeframe),
        "token": token,
    }
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
