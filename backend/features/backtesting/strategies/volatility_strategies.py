"""Volatility and price-level strategy signal generators."""
import numpy as np
import pandas as pd

from features.backtesting.strategies.helpers import (
    _calc_atr,
    _calc_vwap,
    _extract_ohlcv,
    _reindex_to_df,
)


def atr_trailing_stop_signals(
    df: pd.DataFrame,
    atr_period: int = 14,
    atr_multiplier: float = 3.0,
    trend_ma: int = 50,
) -> tuple[pd.Series, pd.Series]:
    """ATR trailing stop strategy.

    Entry when price closes above the trend MA (uptrend confirmation).
    Exit when price closes below the ATR trailing stop level
    (close minus atr_multiplier * ATR).
    """
    _, _, _, close, _ = _extract_ohlcv(df)
    _, high, low, _, _ = _extract_ohlcv(df)
    atr = _calc_atr(high, low, close, atr_period)
    trend = close.rolling(trend_ma).mean()
    above_trend = close > trend
    prev_above = above_trend.shift(1).infer_objects(copy=False).fillna(False)
    entries = above_trend & ~prev_above
    trailing_stop = close - atr_multiplier * atr
    exits = close < trailing_stop
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def vwap_cross_signals(
    df: pd.DataFrame,
    band_pct: float = 0.0,
) -> tuple[pd.Series, pd.Series]:
    """VWAP crossover strategy.

    Entry when close crosses above VWAP (+ optional band percentage).
    Exit when close crosses below VWAP.
    """
    _, high, low, close, volume = _extract_ohlcv(df)
    vwap = _calc_vwap(high, low, close, volume)
    upper = vwap * (1 + band_pct)
    above = close > upper
    prev_above = above.shift(1).infer_objects(copy=False).fillna(False)
    entries = above & ~prev_above
    exits = ~above & prev_above
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def grid_trading_signals(
    df: pd.DataFrame,
    grid_size: float = 0.02,
    num_levels: int = 5,
) -> tuple[pd.Series, pd.Series]:
    """Grid trading strategy.

    Establishes a rolling baseline (mean of recent highs and lows).
    Entry when price drops to or below a grid level below baseline.
    Exit when price rises to or above a grid level above baseline.

    grid_size is the percentage step between grid levels.
    """
    _, high, low, close, _ = _extract_ohlcv(df)
    lookback = num_levels * 10
    baseline = close.rolling(lookback).mean()
    lower_grid = baseline * (1 - grid_size * num_levels)
    upper_grid = baseline * (1 + grid_size * num_levels)
    at_lower = close <= lower_grid
    prev_at_lower = at_lower.shift(1).infer_objects(copy=False).fillna(False)
    entries = at_lower & ~prev_at_lower
    at_upper = close >= upper_grid
    prev_at_upper = at_upper.shift(1).infer_objects(copy=False).fillna(False)
    exits = at_upper & ~prev_at_upper
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def wedge_compression_signals(
    df: pd.DataFrame,
    atr_period: int = 14,
    compression_lookback: int = 20,
    compression_ratio: float = 0.5,
) -> tuple[pd.Series, pd.Series]:
    """Horizontal/wedge compression breakout strategy.

    Entry when ATR is at a multi-period low (spring being coiled)
    AND price closes above the recent high (explosive breakout).
    Exit when ATR expands back to its rolling mean (volatility normalises).
    """
    _, high, low, close, _ = _extract_ohlcv(df)
    atr = _calc_atr(high, low, close, atr_period)
    atr_min = atr.rolling(compression_lookback).min()
    atr_mean = atr.rolling(compression_lookback).mean()
    compressed = atr <= atr_min * (1 + compression_ratio)
    recent_high = high.rolling(compression_lookback).max()
    breakout = close > recent_high.shift(1)
    entries = compressed & breakout
    exits = atr > atr_mean
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)
