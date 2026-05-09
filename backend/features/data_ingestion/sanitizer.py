"""OHLCV data sanitization pipeline."""
from dataclasses import dataclass, field
from datetime import timedelta

import numpy as np
import pandas as pd

from utils.logging import get_logger
from utils.time_utils import timeframe_to_timedelta

logger = get_logger(__name__)

MAX_FILL_CONSECUTIVE = 5   # flag gaps larger than this many bars


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rows_checked: int = 0
    rows_dropped: int = 0


def detect_gaps(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Return a DataFrame of detected time-series gaps.

    Expects df with a 'time' column (tz-aware datetime) sorted ascending.
    """
    if df.empty:
        return pd.DataFrame(columns=["gap_start", "gap_end", "missing_bars"])

    step = timeframe_to_timedelta(timeframe)
    df_sorted = df.sort_values("time").reset_index(drop=True)
    times = df_sorted["time"]

    gaps = []
    for i in range(1, len(times)):
        expected = times.iloc[i - 1] + step
        actual = times.iloc[i]
        if actual > expected:
            missing = int((actual - expected) / step)
            gaps.append({
                "gap_start": expected,
                "gap_end": actual,
                "missing_bars": missing,
            })

    gap_df = pd.DataFrame(gaps)
    if not gap_df.empty:
        logger.warning("gaps_detected", timeframe=timeframe, gap_count=len(gap_df))
    return gap_df


def forward_fill_gaps(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Fill short gaps via forward-fill; flag large gaps instead of filling.

    Returns the filled DataFrame with a 'filled' boolean column.
    """
    if df.empty:
        return df

    step = timeframe_to_timedelta(timeframe)
    df_sorted = df.sort_values("time").reset_index(drop=True)
    df_sorted["filled"] = False

    ohlcv_cols = ["open", "high", "low", "close", "volume"]
    new_rows: list[dict] = []

    for i in range(1, len(df_sorted)):
        prev = df_sorted.iloc[i - 1]
        curr = df_sorted.iloc[i]
        gap_steps = int((curr["time"] - prev["time"]) / step) - 1

        if 0 < gap_steps <= MAX_FILL_CONSECUTIVE:
            for j in range(1, gap_steps + 1):
                filled_row = prev.to_dict()
                filled_row["time"] = prev["time"] + j * step
                filled_row["volume"] = 0
                filled_row["filled"] = True
                new_rows.append(filled_row)
        elif gap_steps > MAX_FILL_CONSECUTIVE:
            logger.warning("large_gap_not_filled", gap_steps=gap_steps, time=str(curr["time"]))

    if new_rows:
        extra = pd.DataFrame(new_rows)
        df_sorted = pd.concat([df_sorted, extra], ignore_index=True)
        df_sorted = df_sorted.sort_values("time").reset_index(drop=True)

    return df_sorted


def adjust_splits_dividends(df: pd.DataFrame, events: list[dict]) -> pd.DataFrame:
    """Apply corporate action adjustments (splits & dividends) to OHLCV.

    events: list of dicts with keys: date (datetime), split_ratio (float), dividend (float).
    """
    if df.empty or not events:
        return df

    df = df.sort_values("time").reset_index(drop=True)

    for event in sorted(events, key=lambda e: e["date"], reverse=True):
        event_date = pd.Timestamp(event["date"])
        split_ratio = float(event.get("split_ratio", 1.0))
        dividend = float(event.get("dividend", 0.0))

        mask = df["time"] < event_date

        if split_ratio != 1.0 and split_ratio > 0:
            for col in ["open", "high", "low", "close"]:
                df.loc[mask, col] = df.loc[mask, col] / split_ratio
            df.loc[mask, "volume"] = (df.loc[mask, "volume"] * split_ratio).astype(int)

        if dividend > 0:
            close_before = df.loc[mask, "close"]
            if not close_before.empty:
                adjustment_factor = 1 - dividend / close_before.iloc[-1]
                for col in ["open", "high", "low", "close"]:
                    df.loc[mask, col] = df.loc[mask, col] * adjustment_factor

    return df


def validate_ohlcv(df: pd.DataFrame) -> ValidationResult:
    """Validate OHLCV integrity. Returns ValidationResult with errors/warnings."""
    result = ValidationResult(is_valid=True, rows_checked=len(df))

    if df.empty:
        result.warnings.append("DataFrame is empty")
        return result

    required_cols = {"time", "open", "high", "low", "close", "volume"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        result.is_valid = False
        result.errors.append(f"Missing required columns: {missing_cols}")
        return result

    null_mask = df[list(required_cols)].isnull().any(axis=1)
    null_count = null_mask.sum()
    if null_count > 0:
        result.errors.append(f"{null_count} rows have null values in required columns")
        result.is_valid = False

    bad_hl = df["high"] < df["low"]
    if bad_hl.any():
        result.errors.append(f"{bad_hl.sum()} rows have high < low")
        result.is_valid = False

    bad_vol = df["volume"] < 0
    if bad_vol.any():
        result.errors.append(f"{bad_vol.sum()} rows have negative volume")
        result.is_valid = False

    neg_prices = (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
    if neg_prices.any():
        result.warnings.append(f"{neg_prices.sum()} rows have non-positive prices")

    dup = df.duplicated(subset=["time"])
    if dup.any():
        result.warnings.append(f"{dup.sum()} duplicate timestamps detected")

    return result


def run_sanitization_pipeline(df: pd.DataFrame, timeframe: str, events: list[dict] | None = None) -> pd.DataFrame:
    """Orchestrate full sanitization: validate → adjust → fill gaps."""
    validation = validate_ohlcv(df)
    if not validation.is_valid:
        logger.error("ohlcv_validation_failed", errors=validation.errors)
        raise ValueError(f"OHLCV validation failed: {validation.errors}")

    if validation.warnings:
        logger.warning("ohlcv_validation_warnings", warnings=validation.warnings)

    df = adjust_splits_dividends(df, events or [])
    df = forward_fill_gaps(df, timeframe)

    return df
