"""Momentum-based strategy signal generators."""
import pandas as pd

from features.backtesting.strategies.helpers import (
    _calc_aroon,
    _calc_laguerre_rsi,
    _calc_macd,
    _calc_rsi,
    _calc_stoch_rsi,
    _extract_ohlcv,
    _reindex_to_df,
)


def macd_signals(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series]:
    """MACD crossover strategy.

    Entry when MACD line crosses above signal line.
    Exit when MACD line crosses below signal line.
    """
    _, _, _, close, _ = _extract_ohlcv(df)
    macd_line, signal_line, _ = _calc_macd(close, fast, slow, signal)
    above = macd_line > signal_line
    prev_above = above.shift(1).infer_objects(copy=False).fillna(False)
    entries = above & ~prev_above
    exits = ~above & prev_above
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def rsi_signals(
    df: pd.DataFrame,
    period: int = 14,
    overbought: float = 70.0,
    oversold: float = 30.0,
) -> tuple[pd.Series, pd.Series]:
    """RSI overbought/oversold mean-reversion strategy.

    Entry when RSI crosses back above oversold level.
    Exit when RSI crosses back below overbought level.
    """
    _, _, _, close, _ = _extract_ohlcv(df)
    rsi = _calc_rsi(close, period)
    was_oversold = rsi.shift(1) < oversold
    entries = was_oversold & (rsi >= oversold)
    was_overbought = rsi.shift(1) > overbought
    exits = was_overbought & (rsi <= overbought)
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def lrsi_signals(
    df: pd.DataFrame,
    gamma: float = 0.5,
    overbought: float = 0.8,
    oversold: float = 0.2,
) -> tuple[pd.Series, pd.Series]:
    """Laguerre RSI strategy — smoother RSI reducing noise.

    Entry when LRSI crosses back above oversold level.
    Exit when LRSI crosses back below overbought level.
    """
    _, _, _, close, _ = _extract_ohlcv(df)
    lrsi = _calc_laguerre_rsi(close, gamma)
    was_oversold = lrsi.shift(1) < oversold
    entries = was_oversold & (lrsi >= oversold)
    was_overbought = lrsi.shift(1) > overbought
    exits = was_overbought & (lrsi <= overbought)
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def new_high_low_signals(
    df: pd.DataFrame,
    lookback: int = 252,
) -> tuple[pd.Series, pd.Series]:
    """New 52-week high/low momentum breakout.

    Entry when close makes a new N-period high (momentum continuation).
    Exit when close makes a new N-period low.
    """
    _, _, _, close, _ = _extract_ohlcv(df)
    rolling_high = close.rolling(lookback).max()
    rolling_low = close.rolling(lookback).min()
    at_high = close >= rolling_high
    prev_at_high = at_high.shift(1).infer_objects(copy=False).fillna(False)
    entries = at_high & ~prev_at_high
    at_low = close <= rolling_low
    prev_at_low = at_low.shift(1).infer_objects(copy=False).fillna(False)
    exits = at_low & ~prev_at_low
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def aroon_signals(
    df: pd.DataFrame,
    period: int = 52,
    threshold: float = 50.0,
) -> tuple[pd.Series, pd.Series]:
    """Aroon 52 trend-following strategy.

    Entry when Aroon Up crosses above Aroon Down and Aroon Up > threshold.
    Exit when Aroon Down crosses above Aroon Up.
    """
    _, high, low, _, _ = _extract_ohlcv(df)
    aroon_up, aroon_down = _calc_aroon(high, low, period)
    up_above = aroon_up > aroon_down
    prev_up_above = up_above.shift(1).infer_objects(copy=False).fillna(False)
    entries = up_above & ~prev_up_above & (aroon_up > threshold)
    exits = ~up_above & prev_up_above
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def stoch_rsi_signals(
    df: pd.DataFrame,
    rsi_period: int = 14,
    stoch_period: int = 14,
    smooth_k: int = 3,
    smooth_d: int = 3,
    overbought: float = 0.8,
    oversold: float = 0.2,
) -> tuple[pd.Series, pd.Series]:
    """Stochastic RSI oscillator strategy.

    Entry when %K crosses above %D from below the oversold level.
    Exit when %K crosses below %D from above the overbought level.
    """
    _, _, _, close, _ = _extract_ohlcv(df)
    k, d = _calc_stoch_rsi(close, rsi_period, stoch_period, smooth_k, smooth_d)
    was_oversold = k.shift(1) < oversold
    k_above_d = k > d
    prev_k_above_d = k_above_d.shift(1).infer_objects(copy=False).fillna(False)
    entries = was_oversold & k_above_d & ~prev_k_above_d
    was_overbought = k.shift(1) > overbought
    k_below_d = k < d
    prev_k_below_d = k_below_d.shift(1).infer_objects(copy=False).fillna(False)
    exits = was_overbought & k_below_d & ~prev_k_below_d
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def momentum_rotation_signals(
    df: pd.DataFrame,
    short_window: int = 20,
    long_window: int = 60,
    threshold: float = 0.0,
) -> tuple[pd.Series, pd.Series]:
    """Momentum rotation — buy when short-term return exceeds long-term return.

    Entry: short-term rolling return > long-term rolling return + threshold.
    Exit: short-term rolling return falls below long-term rolling return.
    """
    _, _, _, close, _ = _extract_ohlcv(df)
    short_ret = close.pct_change(short_window)
    long_ret = close.pct_change(long_window)
    outperforming = short_ret > (long_ret + threshold)
    prev_outperforming = outperforming.shift(1).infer_objects(copy=False).fillna(False)
    entries = outperforming & ~prev_outperforming
    exits = ~outperforming & prev_outperforming
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)
