from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from config import get_settings

EXECUTION_TIMEFRAMES = frozenset({"5m", "15m", "30m", "1h", "4h", "1d", "1w", "1mo"})

_INTRADAY_TIMEFRAMES = frozenset({"5m", "15m", "30m", "1h", "4h"})
_DAILY_PLUS_TIMEFRAMES = frozenset({"1d", "1w", "1mo"})

# Native Tiingo fetch timeframe for each deployment timeframe.
_NATIVE_FETCH: dict[str, str] = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "1h",
    "1d": "1d",
    "1w": "1d",
    "1mo": "1d",
}

# US regular session (ET) — 9:30–16:00, approximated in UTC (no DST handling in MVP).
_US_SESSION_START_HOUR_UTC = 14
_US_SESSION_END_HOUR_UTC = 22


@dataclass(frozen=True)
class FetchTarget:
    symbol: str
    native_timeframe: str
    source: str
    derive_4h: bool = False


def validate_execution_timeframe(timeframe: str) -> None:
    if timeframe not in EXECUTION_TIMEFRAMES:
        supported = ", ".join(sorted(EXECUTION_TIMEFRAMES))
        raise ValueError(
            f"Unsupported deployment timeframe: {timeframe}. Supported: {supported}"
        )


def native_fetch_timeframe(deployment_timeframe: str) -> str:
    validate_execution_timeframe(deployment_timeframe)
    return _NATIVE_FETCH[deployment_timeframe]


def tiingo_source_for_asset(asset_type: str, native_timeframe: str) -> str:
    """Return Tiingo-only source (used for historical backfill defaults)."""
    if asset_type == "crypto":
        return "tiingo_crypto"
    if native_timeframe == "1d":
        return "tiingo_eod"
    return "tiingo_iex"


def ingest_source_for_asset(asset_type: str, native_timeframe: str) -> str:
    """Return preferred OHLCV ingest source for deployment refresh and freshness checks."""
    if asset_type == "crypto":
        if native_timeframe == "1d":
            return "tiingo_crypto"
        if get_settings().crypto_intraday_source.lower() == "alpaca":
            return "alpaca_crypto"
        return "tiingo_crypto"
    if native_timeframe == "1d":
        return "tiingo_eod"
    return "tiingo_iex"


def needs_4h_derivation(deployment_timeframe: str) -> bool:
    return deployment_timeframe == "4h"


def is_intraday_timeframe(timeframe: str) -> bool:
    return timeframe in _INTRADAY_TIMEFRAMES


def is_us_regular_session(as_of: datetime) -> bool:
    utc = as_of.astimezone(timezone.utc)
    if utc.weekday() >= 5:
        return False
    hour = utc.hour + utc.minute / 60.0
    return _US_SESSION_START_HOUR_UTC <= hour < _US_SESSION_END_HOUR_UTC


def should_evaluate_timeframe(
    timeframe: str,
    as_of: datetime,
    *,
    asset_type: str = "stock",
) -> bool:
    validate_execution_timeframe(timeframe)
    utc = as_of.astimezone(timezone.utc)

    if timeframe in _INTRADAY_TIMEFRAMES:
        if asset_type != "crypto" and not is_us_regular_session(utc):
            return False
        return _intraday_boundary(timeframe, utc)

    if timeframe == "1d":
        return utc.hour == 22 and utc.minute >= 10

    if timeframe == "1w":
        return utc.weekday() == 0 and utc.hour == 22 and utc.minute >= 10

    if timeframe == "1mo":
        return utc.day == 1 and utc.hour == 22 and utc.minute >= 10

    return False


def _intraday_boundary(timeframe: str, utc: datetime) -> bool:
    minute = utc.minute
    if timeframe == "5m":
        return minute % 5 == 0
    if timeframe == "15m":
        return minute % 15 == 0
    if timeframe == "30m":
        return minute % 30 == 0
    if timeframe == "1h":
        return minute == 0
    if timeframe == "4h":
        return minute == 0 and utc.hour % 4 == 0
    return False


def due_execution_timeframes(
    as_of: datetime,
    *,
    asset_type: str = "stock",
) -> list[str]:
    return [
        tf
        for tf in sorted(EXECUTION_TIMEFRAMES)
        if should_evaluate_timeframe(tf, as_of, asset_type=asset_type)
    ]


def floor_to_cron_slot(dt: datetime) -> datetime:
    utc = dt.astimezone(timezone.utc).replace(second=0, microsecond=0)
    return utc.replace(minute=(utc.minute // 5) * 5)


def bar_time_for_evaluation_slot(slot: datetime, timeframe: str) -> datetime:
    validate_execution_timeframe(timeframe)
    utc = slot.astimezone(timezone.utc)
    if timeframe == "5m":
        return utc - timedelta(minutes=5)
    if timeframe == "15m":
        return utc - timedelta(minutes=15)
    if timeframe == "30m":
        return utc - timedelta(minutes=30)
    if timeframe == "1h":
        return utc - timedelta(hours=1)
    if timeframe == "4h":
        return utc - timedelta(hours=4)
    if timeframe in _DAILY_PLUS_TIMEFRAMES:
        return (utc - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return utc


def expected_boundaries(
    timeframe: str,
    start: datetime,
    end: datetime,
    *,
    asset_type: str = "stock",
) -> list[datetime]:
    validate_execution_timeframe(timeframe)
    if end <= start:
        return []
    slot = floor_to_cron_slot(start)
    end_utc = end.astimezone(timezone.utc)
    boundaries: list[datetime] = []
    while slot <= end_utc:
        if should_evaluate_timeframe(timeframe, slot, asset_type=asset_type):
            boundaries.append(slot)
        slot += timedelta(minutes=5)
    return boundaries
