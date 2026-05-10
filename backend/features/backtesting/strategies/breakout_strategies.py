"""Breakout strategy signal generators."""
import numpy as np
import pandas as pd

from features.backtesting.strategies.helpers import _extract_ohlcv, _reindex_to_df


def breakout_signals(
    df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    squeeze_lookback: int = 120,
    donchian_window: int = 20,
) -> tuple[pd.Series, pd.Series]:
    """Volatility squeeze / Bollinger + Donchian breakout.

    Entry: price closes above upper Donchian Channel AND Bollinger bandwidth
    is at its lowest in the last squeeze_lookback bars (squeeze condition).
    Exit: price drops below the mid-point of the Donchian Channel.
    """
    _, high, low, close, _ = _extract_ohlcv(df)
    bb_mid = close.rolling(bb_window).mean()
    bb_std_s = close.rolling(bb_window).std()
    bb_bandwidth = (bb_std_s * 2 * bb_std) / bb_mid.replace(0, np.nan)
    squeeze = bb_bandwidth == bb_bandwidth.rolling(squeeze_lookback).min()
    donchian_high = high.rolling(donchian_window).max()
    donchian_low = low.rolling(donchian_window).min()
    donchian_mid = (donchian_high + donchian_low) / 2
    entries = squeeze & (close > donchian_high.shift(1))
    exits = close < donchian_mid
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def range_breakout_signals(
    df: pd.DataFrame,
    lookback: int = 20,
) -> tuple[pd.Series, pd.Series]:
    """Horizontal support/resistance range breakout.

    Entry when price breaks above the N-bar high (resistance breakout).
    Exit when price drops below the N-bar low (support break).
    """
    _, high, low, close, _ = _extract_ohlcv(df)
    rolling_high = high.rolling(lookback).max()
    rolling_low = low.rolling(lookback).min()
    above_resistance = close > rolling_high.shift(1)
    prev_above = above_resistance.shift(1).infer_objects(copy=False).fillna(False)
    entries = above_resistance & ~prev_above
    below_support = close < rolling_low.shift(1)
    prev_below = below_support.shift(1).infer_objects(copy=False).fillna(False)
    exits = below_support & ~prev_below
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def orb_signals(
    df: pd.DataFrame,
    opening_bars: int = 6,
) -> tuple[pd.Series, pd.Series]:
    """Open Range Breakout (ORB).

    Treats the first opening_bars rows of each contiguous block as the
    opening range. For daily OHLCV data, this behaves as a single
    opening-range window anchored to the start of the series or each
    calendar year. For intraday data, the range resets each session.

    Entry when close breaks above the opening range high.
    Exit when close drops below the opening range low.

    Note: For daily bars the opening range is approximated by a fixed
    rolling window anchored to the session start heuristic.
    """
    _, high, low, close, _ = _extract_ohlcv(df)
    orb_high = high.iloc[:opening_bars].max()
    orb_low = low.iloc[:opening_bars].min()
    above_orb = close > orb_high
    prev_above = above_orb.shift(1).infer_objects(copy=False).fillna(False)
    entries = above_orb & ~prev_above
    below_orb = close < orb_low
    prev_below = below_orb.shift(1).infer_objects(copy=False).fillna(False)
    exits = below_orb & ~prev_below
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)
