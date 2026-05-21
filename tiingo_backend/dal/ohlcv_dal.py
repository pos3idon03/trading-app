from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from dtos.market_data_dto import OHLCVRecord
from features.market_data.ohlcv_resample import (
    compute_resample_start,
    get_resampled_bars,
    intraday_source_candidates,
    is_tail_timeframe,
    resolve_ohlcv_query,
)
from models.market_data import OHLCV
from utils.logging import get_logger

logger = get_logger(__name__)

_SOURCE_PRIORITY: dict[str, list[str]] = {
    "1d": ["tiingo_crypto", "tiingo_eod", "tiingo_iex"],
    "5m": ["tiingo_iex", "tiingo_crypto"],
    "1m": ["tiingo_iex", "tiingo_crypto"],
    "15m": ["tiingo_iex", "tiingo_crypto"],
    "30m": ["tiingo_iex", "tiingo_crypto"],
    "1h": ["tiingo_iex", "tiingo_crypto"],
    "4h": ["tiingo_iex", "tiingo_crypto"],
    "1w": ["tiingo_eod", "tiingo_iex"],
    "1mo": ["tiingo_eod", "tiingo_iex"],
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


def _rows_to_bars(rows) -> list[dict]:
    return [
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


def _dedupe_daily_bars(bars: list[dict]) -> list[dict]:
    by_day: dict = {}
    for bar in bars:
        t = bar["time"]
        day = t.date() if hasattr(t, "date") else t
        by_day[day] = bar
    return sorted(by_day.values(), key=lambda b: b["time"])


async def get_bars(
    session: AsyncSession,
    instrument_id: int,
    timeframe: str,
    *,
    source: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 2000,
    fetch_tail: bool = False,
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

    if fetch_tail:
        q = q.order_by(OHLCV.time.desc()).limit(limit)
    else:
        q = q.order_by(OHLCV.time.asc()).limit(limit)

    rows = (await session.execute(q)).scalars().all()
    if fetch_tail:
        rows = list(reversed(rows))
    bars = _rows_to_bars(rows)
    if timeframe == "1d":
        bars = _dedupe_daily_bars(bars)
    return bars, resolved_source


async def get_bars_with_resample(
    session: AsyncSession,
    instrument_id: int,
    timeframe: str,
    *,
    source: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 2000,
    fetch_tail: bool = False,
) -> tuple[list[dict], Optional[str]]:
    tail = fetch_tail or is_tail_timeframe(timeframe)

    bars, resolved_source = await get_bars(
        session, instrument_id, timeframe,
        source=source, start=start, end=end, limit=limit, fetch_tail=tail,
    )
    if bars:
        return bars, resolved_source

    plan = resolve_ohlcv_query(timeframe)
    if plan.bucket_interval is None:
        return [], None

    effective_end = end or datetime.now(timezone.utc)
    effective_start = compute_resample_start(
        effective_end,
        limit,
        plan.bucket_interval,
        explicit_start=start,
    )

    source_candidates = (
        intraday_source_candidates()
        if plan.source_timeframe in intraday_source_candidates()
        else (plan.source_timeframe,)
    )

    for source_tf in source_candidates:
        resolved = await resolve_best_source(session, instrument_id, source_tf, source)
        if not resolved:
            logger.debug(
                "ohlcv_resample_no_source",
                instrument_id=instrument_id,
                source_timeframe=source_tf,
            )
            continue
        try:
            bars = await get_resampled_bars(
                session,
                instrument_id,
                timeframe,
                source_tf,
                plan.bucket_interval,
                source=resolved,
                start=effective_start,
                end=effective_end,
                limit=limit,
                fetch_tail=tail,
            )
        except Exception as exc:
            logger.warning(
                "ohlcv_resample_failed",
                instrument_id=instrument_id,
                timeframe=timeframe,
                source_timeframe=source_tf,
                error=str(exc),
            )
            continue
        if bars:
            logger.info(
                "ohlcv_resample_ok",
                instrument_id=instrument_id,
                timeframe=timeframe,
                source_timeframe=source_tf,
                count=len(bars),
            )
            return bars, resolved

    return [], None


def default_start_for_timeframe(timeframe: str) -> datetime:
    now = datetime.now(timezone.utc)
    if timeframe == "1mo":
        return now - timedelta(days=365 * 10)
    if timeframe == "1w":
        return now - timedelta(days=365 * 5)
    if timeframe == "1d":
        return now - timedelta(days=365 * 30)
    if timeframe in ("4h", "1h", "30m", "15m"):
        return now - timedelta(days=90)
    return now - timedelta(days=5)
