"""Regime weighting utilities for blended MC models."""
import numpy as np
import pandas as pd

DEFAULT_ADX_LOW = 15.0
DEFAULT_ADX_HIGH = 25.0


def calc_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Average Directional Index from OHLC series."""
    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    dm_plus = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=high.index,
    )
    dm_minus = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=high.index,
    )

    atr = tr.ewm(span=period, adjust=False).mean()
    di_plus = 100 * dm_plus.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)
    di_minus = 100 * dm_minus.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)
    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    return dx.ewm(span=period, adjust=False).mean()


def trend_weight_from_adx(
    adx: float,
    low: float = DEFAULT_ADX_LOW,
    high: float = DEFAULT_ADX_HIGH,
) -> float:
    """Map ADX to trend weight in [0, 1]; high ADX favors trend (Merton)."""
    if not np.isfinite(adx):
        return 0.5
    if high <= low:
        return 1.0 if adx >= high else 0.0
    weight = (float(adx) - low) / (high - low)
    return float(np.clip(weight, 0.0, 1.0))
