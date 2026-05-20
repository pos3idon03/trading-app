"""Intraday helpers for Monte Carlo backtest and simulation."""

INTRADAY_TIMEFRAMES = frozenset({"5m", "15m", "30m", "1h", "4h"})
INTRADAY_DATA_LOOKBACK_DAYS = 90
MIN_INTRADAY_CALIBRATION_DAYS = 7


def is_intraday_timeframe(timeframe: str) -> bool:
    return timeframe in INTRADAY_TIMEFRAMES


def default_calibration_days(timeframe: str) -> int:
    if timeframe in ("5m", "15m", "30m"):
        return 30
    if timeframe in ("1h", "4h"):
        return 60
    return 30


def resolve_calibration_lookback_days(
    timeframe: str,
    calibration_years: int,
    calibration_days: int | None = None,
) -> int:
    """Return calibration history length in days for OHLCV fetch and per-bar windows."""
    if is_intraday_timeframe(timeframe):
        days = calibration_days if calibration_days is not None else default_calibration_days(timeframe)
        return min(
            max(days, MIN_INTRADAY_CALIBRATION_DAYS),
            INTRADAY_DATA_LOOKBACK_DAYS,
        )
    return calibration_years * 365


def intraday_ohlcv_error_message(timeframe: str, symbol: str) -> str:
    return (
        f"No {timeframe} OHLCV data for {symbol} in the requested period. "
        "Intraday bars are built from stored 5m data (typically the last ~90 days). "
        "Run data ingestion for this symbol or narrow the simulation date range."
    )
