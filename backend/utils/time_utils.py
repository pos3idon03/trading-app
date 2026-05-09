from datetime import datetime, timezone, timedelta
from typing import Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_iso(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str).astimezone(timezone.utc)


def timeframe_to_timedelta(timeframe: str) -> timedelta:
    mapping = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "30m": timedelta(minutes=30),
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1),
    }
    if timeframe not in mapping:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return mapping[timeframe]


def timeframe_to_seconds(timeframe: str) -> float:
    return timeframe_to_timedelta(timeframe).total_seconds()


def date_range(
    start: datetime,
    end: datetime,
    timeframe: str,
) -> list[datetime]:
    step = timeframe_to_timedelta(timeframe)
    result = []
    current = start
    while current <= end:
        result.append(current)
        current += step
    return result


def days_between(start: datetime, end: Optional[datetime] = None) -> int:
    if end is None:
        end = utcnow()
    return (to_utc(end) - to_utc(start)).days
