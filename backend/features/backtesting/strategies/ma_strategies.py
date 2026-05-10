"""Moving average strategy signal generators."""
import pandas as pd

from features.backtesting.strategies.helpers import _calc_ema, _extract_ohlcv, _reindex_to_df


def ma_crossover_signals(
    df: pd.DataFrame,
    fast_window: int = 10,
    slow_window: int = 50,
) -> tuple[pd.Series, pd.Series]:
    """SMA crossover (fast vs slow). Entry on golden cross, exit on death cross."""
    _, _, _, close, _ = _extract_ohlcv(df)
    fast_ma = close.rolling(fast_window).mean()
    slow_ma = close.rolling(slow_window).mean()
    above = fast_ma > slow_ma
    prev_above = above.shift(1).infer_objects(copy=False).fillna(False)
    entries = above & ~prev_above
    exits = ~above & prev_above
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def sma_cross_signals(
    df: pd.DataFrame,
    fast_window: int = 50,
    slow_window: int = 200,
) -> tuple[pd.Series, pd.Series]:
    """Golden/Death Cross using SMA(50) and SMA(200) by default."""
    _, _, _, close, _ = _extract_ohlcv(df)
    fast_ma = close.rolling(fast_window).mean()
    slow_ma = close.rolling(slow_window).mean()
    above = fast_ma > slow_ma
    prev_above = above.shift(1).infer_objects(copy=False).fillna(False)
    entries = above & ~prev_above
    exits = ~above & prev_above
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def ema_cross_signals(
    df: pd.DataFrame,
    fast_span: int = 12,
    slow_span: int = 26,
) -> tuple[pd.Series, pd.Series]:
    """EMA crossover — reacts faster to price changes than SMA."""
    _, _, _, close, _ = _extract_ohlcv(df)
    fast_ema = _calc_ema(close, fast_span)
    slow_ema = _calc_ema(close, slow_span)
    above = fast_ema > slow_ema
    prev_above = above.shift(1).infer_objects(copy=False).fillna(False)
    entries = above & ~prev_above
    exits = ~above & prev_above
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def sma_break_signals(
    df: pd.DataFrame,
    sma_window: int = 200,
) -> tuple[pd.Series, pd.Series]:
    """Price crossing above/below a single SMA (e.g. 20, 50, 200-day).

    Entry when close crosses above SMA; exit when close crosses below SMA.
    """
    _, _, _, close, _ = _extract_ohlcv(df)
    sma = close.rolling(sma_window).mean()
    above = close > sma
    prev_above = above.shift(1).infer_objects(copy=False).fillna(False)
    entries = above & ~prev_above
    exits = ~above & prev_above
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)
