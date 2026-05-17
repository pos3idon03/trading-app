"""DAL for OHLCV and fundamental market data."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from dtos.market_data_dto import FundamentalRecord, OHLCVRecord
from models.market_data import OHLCV, CompanyProfile, Fundamental
from utils.logging import get_logger

logger = get_logger(__name__)


async def bulk_insert_ohlcv(session: AsyncSession, records: list[OHLCVRecord]) -> int:
    """High-performance bulk insert using PostgreSQL COPY protocol via asyncpg.

    The COPY call is wrapped in a savepoint so that any failure (e.g. a
    duplicate-key violation) only rolls back to the savepoint and leaves the
    outer transaction alive. The ORM upsert fallback can then execute cleanly
    on the same session.
    """
    if not records:
        return 0

    try:
        async with session.begin_nested():
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


def _interval_to_timedelta(interval: str) -> timedelta:
    """Convert an interval string like '15 minutes' or '4 hours' to timedelta.

    asyncpg requires timedelta objects for PostgreSQL INTERVAL bind parameters.
    """
    value, unit = interval.strip().split(None, 1)
    unit = unit.rstrip("s")
    n = int(value)
    if unit == "minute":
        return timedelta(minutes=n)
    if unit == "hour":
        return timedelta(hours=n)
    if unit == "day":
        return timedelta(days=n)
    raise ValueError(f"Unsupported interval string: '{interval}'")


async def get_ohlcv(
    session: AsyncSession,
    asset_id: int,
    timeframe: str,
    start: datetime,
    end: datetime,
    bucket_interval: Optional[Union[str, timedelta]] = None,
) -> pd.DataFrame:
    """Query OHLCV data, optionally resampled via TimescaleDB time_bucket."""
    if bucket_interval:
        # asyncpg requires timedelta objects for INTERVAL bind parameters.
        # Accept either a timedelta directly or a human-readable string such
        # as "15 minutes" / "1 hour" (parsed by _interval_to_timedelta).
        if isinstance(bucket_interval, timedelta):
            bucket_td = bucket_interval
        else:
            bucket_td = _interval_to_timedelta(bucket_interval)
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
                avg(vwap)          AS vwap,
                min(source)        AS source
            FROM ohlcv
            WHERE asset_id = :asset_id
              AND timeframe = :timeframe
              AND time >= :start
              AND time <= :end
            GROUP BY time_bucket(:bucket, time), asset_id
            ORDER BY 1 ASC
        """)
        result = await session.execute(query, {
            "bucket": bucket_td, "asset_id": asset_id,
            "timeframe": timeframe, "start": start, "end": end,
        })
    else:
        # DISTINCT ON (time) ensures one row per timestamp when the same
        # (time, asset_id, timeframe) exists under multiple sources (e.g.
        # polygon + yfinance). ORDER BY time ASC, source ASC picks 'polygon'
        # before 'yfinance' as the preferred source.
        query = text("""
            SELECT DISTINCT ON (time)
                time, open, high, low, close, volume, vwap, source
            FROM ohlcv
            WHERE asset_id = :asset_id
              AND timeframe = :timeframe
              AND time >= :start
              AND time <= :end
            ORDER BY time ASC, source ASC
        """)
        result = await session.execute(query, {
            "asset_id": asset_id, "timeframe": timeframe,
            "start": start, "end": end,
        })

        df = pd.DataFrame(list(result.mappings().all()))
        return _sanitize_nan(df)

    df = pd.DataFrame(result.mappings().all())
    return _sanitize_nan(df)


def _sanitize_nan(df: pd.DataFrame) -> pd.DataFrame:
    """Replace NaN/Inf float values with Python None so they are JSON-serializable.

    Converts to object dtype so that None is preserved as a Python object
    rather than being coerced back to np.nan by float columns.
    """
    if df.empty:
        return df
    return df.astype(object).where(df.notna(), other=None)


# Maps a requested timeframe to (TimescaleDB bucket interval, source timeframe stored in DB).
# Used when the exact timeframe has no rows but can be derived from finer-grained stored data.
_RESAMPLE_MAP: dict[str, tuple[str, str]] = {
    "15m": ("15 minutes", "5m"),
    "30m": ("30 minutes", "5m"),
    "1h":  ("1 hour",     "5m"),
    "4h":  ("4 hours",    "5m"),
}


async def resample_ohlcv(
    session: AsyncSession,
    asset_id: int,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> "pd.DataFrame":
    """Attempt to build bars for `timeframe` by resampling from a finer stored granularity.

    Returns an empty DataFrame when no resample path exists or the source data is absent.
    """
    entry = _RESAMPLE_MAP.get(timeframe)
    if entry is None:
        return pd.DataFrame()
    bucket_interval, source_tf = entry
    return await get_ohlcv(session, asset_id, source_tf, start, end, bucket_interval=bucket_interval)


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


async def get_fundamentals(session: AsyncSession, asset_id: int) -> list[dict]:
    """Return the latest value for each scalar fundamental metric (non-statement rows)."""
    query = text("""
        SELECT DISTINCT ON (metric_name)
            metric_name, value, time AS fetched_at
        FROM fundamentals
        WHERE asset_id = :asset_id
          AND metric_name NOT LIKE 'income_stmt.%'
          AND metric_name NOT LIKE 'balance_sheet.%'
          AND metric_name NOT LIKE 'cashflow.%'
        ORDER BY metric_name, time DESC
    """)
    result = await session.execute(query, {"asset_id": asset_id})
    return [dict(r) for r in result.mappings().all()]


async def get_financial_statements(
    session: AsyncSession,
    asset_id: int,
    statement_type: str,
) -> list[dict]:
    """Return rows for a specific statement type, latest value per metric+period."""
    prefix = f"{statement_type}.%"
    query = text("""
        SELECT DISTINCT ON (metric_name, period)
            metric_name, value, period
        FROM fundamentals
        WHERE asset_id = :asset_id
          AND metric_name LIKE :prefix
          AND period IS NOT NULL
        ORDER BY metric_name, period DESC, time DESC
    """)
    result = await session.execute(query, {"asset_id": asset_id, "prefix": prefix})
    return [dict(r) for r in result.mappings().all()]


async def get_company_profile(session: AsyncSession, asset_id: int) -> Optional[dict]:
    """Return the company profile for an asset, or None if not yet ingested."""
    stmt = select(CompanyProfile).where(CompanyProfile.asset_id == asset_id)
    result = await session.execute(stmt)
    row = result.scalars().first()
    if row is None:
        return None
    return {
        "sector": row.sector,
        "industry": row.industry,
        "business_summary": row.business_summary,
        "website": row.website,
        "country": row.country,
        "employees": row.employees,
        "officers": row.officers or [],
        "source": row.source,
        "fetched_at": row.fetched_at,
    }


async def upsert_company_profile(session: AsyncSession, asset_id: int, data: dict) -> None:
    """Insert or replace the company profile for an asset."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(CompanyProfile).values(
        asset_id=asset_id,
        sector=data.get("sector"),
        industry=data.get("industry"),
        business_summary=data.get("business_summary"),
        website=data.get("website"),
        country=data.get("country"),
        employees=data.get("employees"),
        officers=data.get("officers", []),
        source=data.get("source", "yfinance"),
        fetched_at=datetime.now(timezone.utc),
    )
    update_cols = {
        c: stmt.excluded[c]
        for c in ["sector", "industry", "business_summary", "website",
                  "country", "employees", "officers", "source", "fetched_at"]
    }
    stmt = stmt.on_conflict_do_update(index_elements=["asset_id"], set_=update_cols)
    await session.execute(stmt)


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


async def list_assets_with_latest_price(session: AsyncSession) -> list[dict]:
    """Return all assets with their latest daily close price and timestamp."""
    query = text("""
        SELECT
            a.id,
            a.symbol,
            a.name,
            a.asset_type,
            a.exchange,
            a.currency,
            a.is_active,
            latest.close  AS latest_close,
            latest.time   AS latest_update
        FROM assets a
        LEFT JOIN LATERAL (
            SELECT close, time
            FROM ohlcv
            WHERE asset_id = a.id
              AND timeframe = '1d'
            ORDER BY time DESC
            LIMIT 1
        ) latest ON true
        ORDER BY a.symbol ASC
    """)
    result = await session.execute(query)
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def get_asset_id_by_symbol(session: AsyncSession, symbol: str) -> Optional[int]:
    from models.asset import Asset
    stmt = select(Asset.id).where(Asset.symbol == symbol.upper())
    result = await session.execute(stmt)
    row = result.fetchone()
    return row[0] if row else None


async def get_asset_type_by_symbol(session: AsyncSession, symbol: str) -> Optional[str]:
    """Return stored asset_type for a symbol, or None if not registered."""
    from models.asset import Asset
    stmt = select(Asset.asset_type).where(Asset.symbol == symbol.upper())
    result = await session.execute(stmt)
    row = result.fetchone()
    return row[0] if row else None


async def ensure_asset_for_live_stream(session: AsyncSession, symbol: str) -> int:
    """Insert asset row if missing; never overwrite name or other existing fields.

    Live streaming only needs a stable ``asset_id`` for persisted data. Symbols
    that already exist (e.g. after full ingestion with a company name) are left
    unchanged.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from models.asset import Asset

    sym = symbol.upper()
    stmt = (
        pg_insert(Asset)
        .values(symbol=sym, asset_type="stock", currency="USD")
        .on_conflict_do_nothing(index_elements=["symbol"])
    )
    await session.execute(stmt)
    await session.flush()
    asset_id = await get_asset_id_by_symbol(session, sym)
    if asset_id is None:
        raise ValueError(f"asset row missing after ensure: {sym}")
    return asset_id


async def upsert_asset(session: AsyncSession, symbol: str, **kwargs) -> int:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from models.asset import Asset

    symbol = symbol.upper()
    stmt = pg_insert(Asset).values(symbol=symbol, **kwargs)
    stmt = stmt.on_conflict_do_update(index_elements=["symbol"], set_=kwargs)
    result = await session.execute(stmt)
    await session.flush()
    asset_id = await get_asset_id_by_symbol(session, symbol)
    return asset_id


async def delete_asset(session: AsyncSession, symbol: str) -> bool:
    """Delete an asset and all its associated data (cascades to OHLCV, fundamentals, profiles).

    Returns True if a row was deleted, False if the symbol did not exist.
    """
    from sqlalchemy import delete as sql_delete
    from models.asset import Asset

    stmt = sql_delete(Asset).where(Asset.symbol == symbol.upper())
    result = await session.execute(stmt)
    return result.rowcount > 0


async def require_asset_id(session: AsyncSession, symbol: str) -> int:
    """Return the asset id for an existing symbol.

    Raises ValueError if the symbol is not registered in the assets table.
    Only the data ingestion pipeline should create new assets via upsert_asset.
    """
    asset_id = await get_asset_id_by_symbol(session, symbol)
    if asset_id is None:
        raise ValueError(
            f"Asset '{symbol.upper()}' is not registered. "
            "Ingest it first via the /ingest endpoint."
        )
    return asset_id
