from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from dal import ohlcv_dal
from dtos.market_data_dto import OHLCVRecord
from features.market_data.bar_aggregate import aggregate_ohlcv_bars
from utils.logging import get_logger

logger = get_logger(__name__)

_AGGREGATE_TARGETS = {"1h": "4h"}


async def persist_derived_intraday_bars(
    session: AsyncSession,
    instrument_id: int,
    *,
    source_timeframe: str,
    source: str,
    start: datetime,
    end: datetime,
) -> int:
    """Aggregate stored intraday bars (e.g. 1h -> 4h) and upsert derived timeframe rows."""
    target_tf = _AGGREGATE_TARGETS.get(source_timeframe)
    if not target_tf:
        return 0

    bars, _ = await ohlcv_dal.get_bars(
        session,
        instrument_id,
        source_timeframe,
        source=source,
        start=start,
        end=end,
        limit=50_000,
        fetch_tail=False,
    )
    if not bars:
        return 0

    hourly_records = [
        OHLCVRecord(
            time=row["time"],
            instrument_id=instrument_id,
            timeframe=source_timeframe,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row.get("volume") or 0),
            source=row["source"],
        )
        for row in bars
    ]
    aggregated = aggregate_ohlcv_bars(hourly_records, target_tf)
    if not aggregated:
        return 0

    inserted = await ohlcv_dal.bulk_insert_ohlcv(session, aggregated)
    logger.info(
        "intraday_aggregate_persisted",
        instrument_id=instrument_id,
        source_timeframe=source_timeframe,
        target_timeframe=target_tf,
        source=source,
        count=len(aggregated),
        inserted=inserted,
    )
    return inserted
