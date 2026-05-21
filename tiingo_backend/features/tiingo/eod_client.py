from datetime import datetime

import httpx

from dtos.market_data_dto import OHLCVRecord
from features.tiingo.common import get_token, parse_timestamp
from utils.logging import get_logger

logger = get_logger(__name__)

_EOD_BASE = "https://api.tiingo.com/tiingo/daily"

_ADJUSTED_FIELDS = {
    "open": "adjOpen",
    "high": "adjHigh",
    "low": "adjLow",
    "close": "adjClose",
}


def _pick_adjusted_price(row: dict, field: str) -> float:
    adj_key = _ADJUSTED_FIELDS[field]
    adjusted = row.get(adj_key)
    if adjusted is not None:
        return float(adjusted)
    return float(row[field])


async def fetch_eod_bars(
    symbol: str,
    instrument_id: int,
    start: datetime,
    end: datetime,
) -> list[OHLCVRecord]:
    token = get_token()
    url = f"{_EOD_BASE}/{symbol.upper()}/prices"
    params = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "token": token,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        rows = resp.json()

    records = []
    for row in rows:
        records.append(OHLCVRecord(
            time=parse_timestamp(row["date"]),
            instrument_id=instrument_id,
            timeframe="1d",
            open=_pick_adjusted_price(row, "open"),
            high=_pick_adjusted_price(row, "high"),
            low=_pick_adjusted_price(row, "low"),
            close=_pick_adjusted_price(row, "close"),
            volume=int(row.get("volume") or 0),
            source="tiingo_eod",
        ))
    logger.info("eod_fetched", symbol=symbol, count=len(records))
    return records
