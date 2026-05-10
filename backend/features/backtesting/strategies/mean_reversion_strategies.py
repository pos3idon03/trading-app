"""Mean reversion strategy signal generators."""
import numpy as np
import pandas as pd

from features.backtesting.strategies.helpers import (
    _calc_adx,
    _calc_rsi,
    _extract_ohlcv,
    _reindex_to_df,
)


def mean_reversion_signals(
    df: pd.DataFrame,
    lookback: int = 20,
    z_threshold: float = 2.0,
) -> tuple[pd.Series, pd.Series]:
    """Mean reversion using z-score bands.

    Entry (long) when price drops > z_threshold sigma below rolling mean.
    Exit when price returns to mean (z-score crosses 0).
    """
    _, _, _, close, _ = _extract_ohlcv(df)
    rolling_mean = close.rolling(lookback).mean()
    rolling_std = close.rolling(lookback).std()
    z_score = (close - rolling_mean) / rolling_std.replace(0, np.nan)
    entries = z_score < -z_threshold
    exits = z_score > 0
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def mean_reversion_trend_signals(
    df: pd.DataFrame,
    ma_window: int = 50,
    z_threshold: float = 1.5,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
) -> tuple[pd.Series, pd.Series]:
    """Mean reversion to trend — price reverts to its long-term MA in a trending market.

    Requires ADX above threshold (confirming trend) AND price z-score
    below -z_threshold (pulled away from MA).
    Exit when price reverts above the MA (z-score > 0).
    """
    _, high, low, close, _ = _extract_ohlcv(df)
    rolling_mean = close.rolling(ma_window).mean()
    rolling_std = close.rolling(ma_window).std()
    z_score = (close - rolling_mean) / rolling_std.replace(0, np.nan)
    adx = _calc_adx(high, low, close, adx_period)
    strong_trend = adx > adx_threshold
    entries = strong_trend & (z_score < -z_threshold)
    exits = z_score > 0
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def mean_reversion_range_signals(
    df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    adx_period: int = 14,
    adx_max: float = 20.0,
) -> tuple[pd.Series, pd.Series]:
    """Mean reversion in range — Bollinger band bounce in a low-ADX environment.

    Entry when price is below the lower Bollinger Band AND ADX < adx_max (ranging).
    Exit when price crosses back above the Bollinger middle band.
    """
    _, high, low, close, _ = _extract_ohlcv(df)
    bb_mid = close.rolling(bb_window).mean()
    bb_std_s = close.rolling(bb_window).std()
    bb_lower = bb_mid - bb_std * bb_std_s
    adx = _calc_adx(high, low, close, adx_period)
    in_range = adx < adx_max
    entries = in_range & (close < bb_lower)
    exits = close > bb_mid
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def reverting_market_signals(
    df: pd.DataFrame,
    rsi_period: int = 14,
    rsi_upper: float = 60.0,
    rsi_lower: float = 40.0,
    adx_period: int = 14,
    adx_max: float = 20.0,
) -> tuple[pd.Series, pd.Series]:
    """Reverting market — oscillator strategy for sideways/no-trend conditions.

    Entry when RSI drops below rsi_lower AND market is ranging (ADX < adx_max).
    Exit when RSI rises back above rsi_upper.
    """
    _, high, low, close, _ = _extract_ohlcv(df)
    rsi = _calc_rsi(close, rsi_period)
    adx = _calc_adx(high, low, close, adx_period)
    in_range = adx < adx_max
    entries = in_range & (rsi < rsi_lower)
    exits = rsi > rsi_upper
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)
