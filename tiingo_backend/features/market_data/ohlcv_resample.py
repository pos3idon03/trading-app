from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Union

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

SUPPORTED_TIMEFRAMES = frozenset({"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1mo"})

DAILY_PLUS_TIMEFRAMES = frozenset({"1d", "1w", "1mo"})

_INTRADAY_RESAMPLE: dict[str, timedelta] = {
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
}

_DEFAULT_INTRADAY_SOURCES = ("1m", "5m")

_RESAMPLE_SOURCE_PRIORITY: dict[str, tuple[str, ...]] = {
    "15m": _DEFAULT_INTRADAY_SOURCES,
    "30m": _DEFAULT_INTRADAY_SOURCES,
    "1h": _DEFAULT_INTRADAY_SOURCES,
    "4h": ("1h", "1m", "5m"),
}

_TAIL_WINDOW_BUFFER = 1.2


@dataclass(frozen=True)
class OhlcvQueryPlan:
    source_timeframe: str
    bucket_interval: Optional[Union[timedelta, str]] = None


def resolve_ohlcv_query(timeframe: str) -> OhlcvQueryPlan:
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    if timeframe in _INTRADAY_RESAMPLE:
        sources = resample_source_candidates(timeframe)
        return OhlcvQueryPlan(
            source_timeframe=sources[0],
            bucket_interval=_INTRADAY_RESAMPLE[timeframe],
        )

    if timeframe == "1w":
        return OhlcvQueryPlan(source_timeframe="1d", bucket_interval=timedelta(weeks=1))

    if timeframe == "1mo":
        return OhlcvQueryPlan(source_timeframe="1d", bucket_interval="1 month")

    return OhlcvQueryPlan(source_timeframe=timeframe)


def resample_source_candidates(timeframe: str) -> tuple[str, ...]:
    if timeframe in _RESAMPLE_SOURCE_PRIORITY:
        return _RESAMPLE_SOURCE_PRIORITY[timeframe]
    if timeframe in _INTRADAY_RESAMPLE:
        return _DEFAULT_INTRADAY_SOURCES
    return (timeframe,)


def intraday_source_candidates(timeframe: str | None = None) -> tuple[str, ...]:
    if timeframe is not None:
        return resample_source_candidates(timeframe)
    return _DEFAULT_INTRADAY_SOURCES


def is_tail_timeframe(timeframe: str) -> bool:
    return timeframe not in DAILY_PLUS_TIMEFRAMES


def compute_resample_start(
    end: datetime,
    limit: int,
    bucket_interval: Union[timedelta, str],
    *,
    explicit_start: Optional[datetime] = None,
) -> datetime:
    if explicit_start is not None:
        return explicit_start
    if isinstance(bucket_interval, str):
        return end - timedelta(days=int(limit * 31 * _TAIL_WINDOW_BUFFER))
    window = bucket_interval * limit
    padded = timedelta(seconds=int(window.total_seconds() * _TAIL_WINDOW_BUFFER))
    return end - padded


def _rows_to_bars(rows) -> list[dict]:
    return [
        {
            "time": row.time,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume or 0,
            "source": row.source,
        }
        for row in rows
    ]


def _aggregate_query(bucket_sql: str, *, fetch_tail: bool) -> text:
    order = "DESC" if fetch_tail else "ASC"
    return text(f"""
        SELECT time, open, high, low, close, volume, source
        FROM (
            SELECT
                time_bucket({bucket_sql}, time) AS time,
                first(open, time)  AS open,
                max(high)          AS high,
                min(low)           AS low,
                last(close, time)  AS close,
                sum(volume)        AS volume,
                min(source)        AS source
            FROM ohlcv
            WHERE instrument_id = :instrument_id
              AND timeframe = :source_timeframe
              AND source = :source
              AND time >= :start
              AND time <= :end
            GROUP BY time_bucket({bucket_sql}, time)
            ORDER BY 1 {order}
            LIMIT :limit
        ) bounded
        ORDER BY time ASC
    """)


async def get_resampled_bars(
    session: AsyncSession,
    instrument_id: int,
    requested_timeframe: str,
    source_timeframe: str,
    bucket_interval: Union[timedelta, str],
    *,
    source: str,
    start: datetime,
    end: datetime,
    limit: int,
    fetch_tail: bool = True,
) -> list[dict]:
    del requested_timeframe

    if isinstance(bucket_interval, str):
        query = _aggregate_query("INTERVAL '1 month'", fetch_tail=fetch_tail)
        params = {
            "instrument_id": instrument_id,
            "source_timeframe": source_timeframe,
            "source": source,
            "start": start,
            "end": end,
            "limit": limit,
        }
    else:
        query = _aggregate_query(":bucket", fetch_tail=fetch_tail)
        params = {
            "bucket": bucket_interval,
            "instrument_id": instrument_id,
            "source_timeframe": source_timeframe,
            "source": source,
            "start": start,
            "end": end,
            "limit": limit,
        }

    result = await session.execute(query, params)
    return _rows_to_bars(result)
