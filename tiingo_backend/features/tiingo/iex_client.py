from datetime import datetime

import httpx

from dtos.market_data_dto import OHLCVRecord
from features.tiingo.common import get_token, parse_timestamp, resample_freq
from utils.logging import get_logger

logger = get_logger(__name__)

_IEX_BASE = "https://api.tiingo.com/iex"
_SUPPORTED = {"1m", "5m", "15m", "30m", "1h"}


async def fetch_iex_bars(
    symbol: str,
    instrument_id: int,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> list[OHLCVRecord]:
    if timeframe not in _SUPPORTED:
        raise ValueError(f"IEX unsupported timeframe: {timeframe}")

    token = get_token()
    url = f"{_IEX_BASE}/{symbol.upper()}/prices"
    params = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "resampleFreq": resample_freq(timeframe),
        "columns": "open,high,low,close,volume",
        "token": token,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        rows = resp.json()

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
            source="tiingo_iex",
        )
        for row in rows
    ]
    logger.info("iex_fetched", symbol=symbol, timeframe=timeframe, count=len(records))
    return records
