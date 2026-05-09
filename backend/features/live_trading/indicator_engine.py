"""Technical indicator calculator using pandas-ta on resampled OHLCV bars."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from utils.logging import get_logger

logger = get_logger(__name__)

MIN_BARS_REQUIRED = 30


@dataclass
class IndicatorSnapshot:
    symbol: str
    timeframe: str
    close_price: float
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    vwap: float | None = None
    bb_percent: float | None = None

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "close_price": self.close_price,
            "rsi": self.rsi,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "macd_histogram": self.macd_histogram,
            "bb_upper": self.bb_upper,
            "bb_middle": self.bb_middle,
            "bb_lower": self.bb_lower,
            "vwap": self.vwap,
            "bb_percent": self.bb_percent,
        }


def _build_dataframe(bars: list) -> pd.DataFrame:
    """Convert OHLCVBar list to a pandas DataFrame suitable for pandas-ta."""
    records = [
        {
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        }
        for b in bars
    ]
    df = pd.DataFrame(records)
    df.columns = [c.lower() for c in df.columns]
    return df


def calculate_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    import pandas_ta as ta
    return ta.rsi(close, length=length)


def calculate_macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9,
) -> pd.DataFrame:
    import pandas_ta as ta
    return ta.macd(close, fast=fast, slow=slow, signal=signal)


def calculate_bollinger_bands(
    close: pd.Series, length: int = 20, std: float = 2.0,
) -> pd.DataFrame:
    import pandas_ta as ta
    return ta.bbands(close, length=length, std=std)


def calculate_vwap(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
) -> pd.Series:
    typical_price = (high + low + close) / 3.0
    cumulative_tp_vol = (typical_price * volume).cumsum()
    cumulative_vol = volume.cumsum()
    return cumulative_tp_vol / cumulative_vol.replace(0, np.nan)


def compute_indicators(
    bars: list,
    symbol: str,
    timeframe: str,
    rsi_length: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    bb_length: int = 20,
    bb_std: float = 2.0,
) -> IndicatorSnapshot | None:
    """Compute all indicators from a list of OHLCVBar objects.

    Returns None if not enough data.
    """
    if len(bars) < MIN_BARS_REQUIRED:
        logger.warning(
            "insufficient_bars",
            symbol=symbol,
            bars=len(bars),
            required=MIN_BARS_REQUIRED,
        )
        return None

    df = _build_dataframe(bars)
    close = df["close"]
    latest_close = float(close.iloc[-1])

    snapshot = IndicatorSnapshot(
        symbol=symbol,
        timeframe=timeframe,
        close_price=latest_close,
    )

    _apply_rsi(snapshot, close, rsi_length)
    _apply_macd(snapshot, close, macd_fast, macd_slow, macd_signal)
    _apply_bollinger(snapshot, close, bb_length, bb_std, latest_close)
    _apply_vwap(snapshot, df)

    return snapshot


def _apply_rsi(snap: IndicatorSnapshot, close: pd.Series, length: int) -> None:
    try:
        rsi = calculate_rsi(close, length)
        if rsi is not None and not rsi.empty:
            val = rsi.iloc[-1]
            snap.rsi = round(float(val), 2) if pd.notna(val) else None
    except Exception as exc:
        logger.warning("rsi_calc_error", error=str(exc))


def _apply_macd(
    snap: IndicatorSnapshot, close: pd.Series, fast: int, slow: int, sig: int,
) -> None:
    try:
        macd_df = calculate_macd(close, fast, slow, sig)
        if macd_df is not None and not macd_df.empty:
            row = macd_df.iloc[-1]
            snap.macd = _safe_round(row.iloc[0])
            snap.macd_signal = _safe_round(row.iloc[1])
            snap.macd_histogram = _safe_round(row.iloc[2])
    except Exception as exc:
        logger.warning("macd_calc_error", error=str(exc))


def _apply_bollinger(
    snap: IndicatorSnapshot, close: pd.Series, length: int, std: float, price: float,
) -> None:
    try:
        bb_df = calculate_bollinger_bands(close, length, std)
        if bb_df is not None and not bb_df.empty:
            row = bb_df.iloc[-1]
            snap.bb_lower = _safe_round(row.iloc[0])
            snap.bb_middle = _safe_round(row.iloc[1])
            snap.bb_upper = _safe_round(row.iloc[2])

            if snap.bb_upper and snap.bb_lower and snap.bb_upper != snap.bb_lower:
                snap.bb_percent = round(
                    (price - snap.bb_lower) / (snap.bb_upper - snap.bb_lower), 4
                )
    except Exception as exc:
        logger.warning("bb_calc_error", error=str(exc))


def _apply_vwap(snap: IndicatorSnapshot, df: pd.DataFrame) -> None:
    try:
        vwap = calculate_vwap(df["high"], df["low"], df["close"], df["volume"])
        if vwap is not None and not vwap.empty:
            val = vwap.iloc[-1]
            snap.vwap = round(float(val), 4) if pd.notna(val) else None
    except Exception as exc:
        logger.warning("vwap_calc_error", error=str(exc))


def _safe_round(val, digits: int = 4) -> float | None:
    return round(float(val), digits) if pd.notna(val) else None
