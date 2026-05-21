from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from dtos.market_data_dto import OHLCVRecord
from models.market_data import OHLCV
from utils.logging import get_logger

logger = get_logger(__name__)

_SOURCE_PRIORITY: dict[str, list[str]] = {
    "1d": ["tiingo_eod", "tiingo_iex"],
    "5m": ["tiingo_iex", "tiingo_crypto"],
    "1m": ["tiingo_iex", "tiingo_crypto"],
    "1h": ["tiingo_iex", "tiingo_crypto"],
}


async def bulk_insert_ohlcv(session: AsyncSession, records: list[OHLCVRecord]) -> int:
    if not records:
        return 0
    try:
        async with session.begin_nested():
            return await _copy_insert(session, records)
    except Exception as exc:
        logger.warning("ohlcv_copy_failed", error=str(exc))
        return await _orm_upsert(session, records)


async def _copy_insert(session: AsyncSession, records: list[OHLCVRecord]) -> int:
    conn = await session.connection()
    raw = await conn.get_raw_connection()
    driver = raw.driver_connection
    rows = [
        (
            r.time, r.instrument_id, r.timeframe,
            r.open, r.high, r.low, r.close,
            r.volume, r.vwap, r.trade_count, r.source,
        )
        for r in records
    ]
    await driver.copy_records_to_table(
        "ohlcv",
        records=rows,
        columns=[
            "time", "instrument_id", "timeframe", "open", "high", "low", "close",
            "volume", "vwap", "trade_count", "source",
        ],
    )
    return len(rows)


async def _orm_upsert(session: AsyncSession, records: list[OHLCVRecord]) -> int:
    stmt = pg_insert(OHLCV).values([
        dict(
            time=r.time, instrument_id=r.instrument_id, timeframe=r.timeframe,
            open=r.open, high=r.high, low=r.low, close=r.close,
            volume=r.volume, vwap=r.vwap, trade_count=r.trade_count, source=r.source,
        )
        for r in records
    ])
    stmt = stmt.on_conflict_do_nothing(constraint="uq_ohlcv")
    result = await session.execute(stmt)
    return result.rowcount or 0


async def get_latest_timestamp(
    session: AsyncSession,
    instrument_id: int,
    timeframe: str,
    source: str,
) -> Optional[datetime]:
    q = select(func.max(OHLCV.time)).where(
        OHLCV.instrument_id == instrument_id,
        OHLCV.timeframe == timeframe,
        OHLCV.source == source,
    )
    result = await session.execute(q)
    return result.scalar_one_or_none()


async def get_coverage(
    session: AsyncSession,
    instrument_id: int,
    timeframe: str,
) -> list[dict]:
    q = text("""
        SELECT source, MIN(time) AS min_time, MAX(time) AS max_time, COUNT(*) AS bar_count
        FROM ohlcv
        WHERE instrument_id = :iid AND timeframe = :tf
        GROUP BY source
        ORDER BY source
    """)
    rows = await session.execute(q, {"iid": instrument_id, "tf": timeframe})
    return [dict(r._mapping) for r in rows]


async def resolve_best_source(
    session: AsyncSession,
    instrument_id: int,
    timeframe: str,
    source: Optional[str] = None,
) -> Optional[str]:
    if source:
        return source
    coverage = await get_coverage(session, instrument_id, timeframe)
    if not coverage:
        return None
    available = {row["source"] for row in coverage}
    for candidate in _SOURCE_PRIORITY.get(timeframe, []):
        if candidate in available:
            return candidate
    return coverage[0]["source"]


async def get_bars(
    session: AsyncSession,
    instrument_id: int,
    timeframe: str,
    *,
    source: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 2000,
) -> tuple[list[dict], Optional[str]]:
    resolved_source = await resolve_best_source(session, instrument_id, timeframe, source)
    if not resolved_source:
        return [], None

    q = select(OHLCV).where(
        OHLCV.instrument_id == instrument_id,
        OHLCV.timeframe == timeframe,
        OHLCV.source == resolved_source,
    )
    if start is not None:
        q = q.where(OHLCV.time >= start)
    if end is not None:
        q = q.where(OHLCV.time <= end)
    q = q.order_by(OHLCV.time.asc()).limit(limit)

    rows = (await session.execute(q)).scalars().all()
    bars = [
        {
            "time": r.time,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
            "source": r.source,
        }
        for r in rows
    ]
    return bars, resolved_source


def default_start_for_timeframe(timeframe: str) -> datetime:
    now = datetime.now(timezone.utc)
    if timeframe == "1d":
        return now - timedelta(days=365)
    return now - timedelta(days=5)
