"""DAL for OHLCV and fundamental market data."""
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from dtos.market_data_dto import FundamentalRecord, OHLCVRecord
from models.market_data import OHLCV, Fundamental
from utils.logging import get_logger

logger = get_logger(__name__)


async def bulk_insert_ohlcv(session: AsyncSession, records: list[OHLCVRecord]) -> int:
    """High-performance bulk insert using PostgreSQL COPY protocol via psycopg2.

    Falls back to ORM upsert when raw connection is unavailable.
    """
    if not records:
        return 0

    try:
        return await _copy_insert_ohlcv(session, records)
    except Exception as exc:
        logger.warning("copy_insert_failed_fallback", error=str(exc))
        return await _orm_upsert_ohlcv(session, records)


async def _copy_insert_ohlcv(session: AsyncSession, records: list[OHLCVRecord]) -> int:
    """High-throughput insert via asyncpg COPY protocol."""
    conn = await session.connection()
    raw = await conn.get_raw_connection()
    driver = raw.driver_connection

    rows = [
        (
            r.time, r.asset_id, r.timeframe,
            r.open, r.high, r.low, r.close,
            r.volume, r.vwap, r.trade_count, r.source,
        )
        for r in records
    ]
    await driver.copy_records_to_table(
        "ohlcv",
        records=rows,
        columns=["time", "asset_id", "timeframe", "open", "high", "low", "close",
                 "volume", "vwap", "trade_count", "source"],
    )
    count = len(rows)
    logger.info("ohlcv_copy_inserted", count=count)
    return count


async def _orm_upsert_ohlcv(session: AsyncSession, records: list[OHLCVRecord]) -> int:
    """Fallback upsert using SQLAlchemy ORM (slower but reliable)."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(OHLCV).values([
        dict(
            time=r.time, asset_id=r.asset_id, timeframe=r.timeframe,
            open=r.open, high=r.high, low=r.low, close=r.close,
            volume=r.volume, vwap=r.vwap, trade_count=r.trade_count, source=r.source,
        )
        for r in records
    ])
    stmt = stmt.on_conflict_do_nothing(constraint="uq_ohlcv")
    result = await session.execute(stmt)
    logger.info("ohlcv_orm_upserted", count=result.rowcount)
    return result.rowcount


async def get_ohlcv(
    session: AsyncSession,
    asset_id: int,
    timeframe: str,
    start: datetime,
    end: datetime,
    bucket_interval: Optional[str] = None,
) -> pd.DataFrame:
    """Query OHLCV data, optionally resampled via TimescaleDB time_bucket."""
    if bucket_interval:
        query = text("""
            SELECT
                time_bucket(:bucket, time) AS time,
                asset_id,
                :timeframe AS timeframe,
                first(open, time)  AS open,
                max(high)          AS high,
                min(low)           AS low,
                last(close, time)  AS close,
                sum(volume)        AS volume,
                avg(vwap)          AS vwap
            FROM ohlcv
            WHERE asset_id = :asset_id
              AND timeframe = :timeframe
              AND time >= :start
              AND time <= :end
            GROUP BY time_bucket(:bucket, time), asset_id
            ORDER BY 1 ASC
        """)
        result = await session.execute(query, {
            "bucket": bucket_interval, "asset_id": asset_id,
            "timeframe": timeframe, "start": start, "end": end,
        })
    else:
        stmt = (
            select(OHLCV)
            .where(OHLCV.asset_id == asset_id)
            .where(OHLCV.timeframe == timeframe)
            .where(OHLCV.time >= start)
            .where(OHLCV.time <= end)
            .order_by(OHLCV.time.asc())
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return pd.DataFrame([{
            "time": r.time, "open": r.open, "high": r.high,
            "low": r.low, "close": r.close, "volume": r.volume,
            "vwap": r.vwap, "source": r.source,
        } for r in rows])

    return pd.DataFrame(result.mappings().all())


async def get_latest_timestamp(
    session: AsyncSession,
    asset_id: int,
    timeframe: str,
) -> Optional[datetime]:
    """Return the most recent timestamp stored for an asset+timeframe (for incremental ingestion)."""
    query = text("""
        SELECT MAX(time) AS latest
        FROM ohlcv
        WHERE asset_id = :asset_id AND timeframe = :timeframe
    """)
    result = await session.execute(query, {"asset_id": asset_id, "timeframe": timeframe})
    row = result.fetchone()
    return row.latest if row else None


async def bulk_insert_fundamentals(session: AsyncSession, records: list[FundamentalRecord]) -> int:
    """Upsert fundamental records."""
    if not records:
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(Fundamental).values([
        dict(
            time=r.time, asset_id=r.asset_id, metric_name=r.metric_name,
            value=r.value, period=r.period, source=r.source,
        )
        for r in records
    ])
    stmt = stmt.on_conflict_do_nothing(constraint="uq_fundamentals")
    result = await session.execute(stmt)
    return result.rowcount


async def list_assets(session: AsyncSession) -> list[dict]:
    """Return all assets ordered by symbol."""
    from models.asset import Asset
    stmt = select(Asset).order_by(Asset.symbol.asc())
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "name": r.name,
            "asset_type": r.asset_type,
            "exchange": r.exchange,
            "currency": r.currency,
            "is_active": r.is_active,
        }
        for r in rows
    ]


async def get_asset_id_by_symbol(session: AsyncSession, symbol: str) -> Optional[int]:
    from models.asset import Asset
    stmt = select(Asset.id).where(Asset.symbol == symbol.upper())
    result = await session.execute(stmt)
    row = result.fetchone()
    return row[0] if row else None


async def upsert_asset(session: AsyncSession, symbol: str, **kwargs) -> int:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from models.asset import Asset

    stmt = pg_insert(Asset).values(symbol=symbol, **kwargs)
    stmt = stmt.on_conflict_do_update(index_elements=["symbol"], set_=kwargs)
    result = await session.execute(stmt)
    await session.flush()
    asset_id = await get_asset_id_by_symbol(session, symbol)
    return asset_id
