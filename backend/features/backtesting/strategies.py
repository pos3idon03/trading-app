"""Strategy signal generators — pure functions returning entry/exit boolean arrays.

Each strategy function accepts a full OHLCV DataFrame with columns:
    open, high, low, close, volume  (DatetimeIndex or 'time' column).

Returns (entries, exits) — boolean pd.Series aligned to the input index.
"""
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_ohlcv(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """Return (open, high, low, close, volume) Series from a standardised OHLCV DataFrame."""
    idx = df.index if "time" not in df.columns else pd.RangeIndex(len(df))
    o = df["open"].astype(float).reset_index(drop=True)
    h = df["high"].astype(float).reset_index(drop=True)
    lo = df["low"].astype(float).reset_index(drop=True)
    c = df["close"].astype(float).reset_index(drop=True)
    v = df["volume"].astype(float).reset_index(drop=True) if "volume" in df.columns else pd.Series(0.0, index=c.index)
    return o, h, lo, c, v


def _reindex_to_df(series: pd.Series, df: pd.DataFrame) -> pd.Series:
    """Restore the original DataFrame index on a computed signal series."""
    series = series.reset_index(drop=True)
    series.index = df.index
    return series


# ---------------------------------------------------------------------------
# Existing strategies (refactored to accept full OHLCV DataFrame)
# ---------------------------------------------------------------------------

def ma_crossover_signals(
    df: pd.DataFrame,
    fast_window: int = 10,
    slow_window: int = 50,
) -> tuple[pd.Series, pd.Series]:
    """Moving average crossover strategy.

    Entry when fast MA crosses above slow MA.
    Exit when fast MA crosses below slow MA.
    """
    _, _, _, close, _ = _extract_ohlcv(df)

    fast_ma = close.rolling(fast_window).mean()
    slow_ma = close.rolling(slow_window).mean()

    above = fast_ma > slow_ma
    prev_above = above.shift(1).infer_objects(copy=False).fillna(False)
    entries = above & ~prev_above
    exits = ~above & prev_above

    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def mean_reversion_signals(
    df: pd.DataFrame,
    lookback: int = 20,
    z_threshold: float = 2.0,
) -> tuple[pd.Series, pd.Series]:
    """Mean reversion strategy using z-score bands.

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


# ---------------------------------------------------------------------------
# New strategies
# ---------------------------------------------------------------------------

def breakout_signals(
    df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    squeeze_lookback: int = 120,
    donchian_window: int = 20,
) -> tuple[pd.Series, pd.Series]:
    """Volatility expansion / breakout strategy.

    Entry: price closes above upper Donchian Channel AND Bollinger bandwidth
    is at its lowest in the last `squeeze_lookback` bars (squeeze condition).
    Exit: price drops below the mid-point of the Donchian Channel.
    """
    _, high, low, close, _ = _extract_ohlcv(df)

    # Bollinger Bands
    bb_mid = close.rolling(bb_window).mean()
    bb_std_s = close.rolling(bb_window).std()
    bb_bandwidth = (bb_std_s * 2 * bb_std) / bb_mid.replace(0, np.nan)

    # Squeeze: bandwidth is at its rolling minimum
    squeeze = bb_bandwidth == bb_bandwidth.rolling(squeeze_lookback).min()

    # Donchian Channel
    donchian_high = high.rolling(donchian_window).max()
    donchian_low = low.rolling(donchian_window).min()
    donchian_mid = (donchian_high + donchian_low) / 2

    entries = squeeze & (close > donchian_high.shift(1))
    exits = close < donchian_mid

    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def _calc_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Compute ADX (Average Directional Index)."""
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    dm_plus = np.where((high - high.shift(1)) > (low.shift(1) - low), high - high.shift(1), 0.0)
    dm_minus = np.where((low.shift(1) - low) > (high - high.shift(1)), low.shift(1) - low, 0.0)
    dm_plus = pd.Series(np.where(np.array(dm_plus) > 0, dm_plus, 0.0), index=high.index)
    dm_minus = pd.Series(np.where(np.array(dm_minus) > 0, dm_minus, 0.0), index=high.index)

    atr = tr.ewm(span=period, adjust=False).mean()
    di_plus = 100 * dm_plus.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)
    di_minus = 100 * dm_minus.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)

    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    adx = dx.ewm(span=period, adjust=False).mean()
    return adx


def _calc_stochastic(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14, smooth: int = 3
) -> tuple[pd.Series, pd.Series]:
    """Compute Stochastic %K and %D."""
    lowest_low = low.rolling(period).min()
    highest_high = high.rolling(period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(smooth).mean()
    return k, d


def trend_pullback_signals(
    df: pd.DataFrame,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
    stoch_period: int = 14,
    stoch_smooth: int = 3,
    oversold: float = 20.0,
    overbought: float = 80.0,
) -> tuple[pd.Series, pd.Series]:
    """Trend-following with pullback entry using ADX + Stochastic Oscillator.

    Entry: ADX > threshold AND Stochastic %K crosses above %D in oversold zone.
    Exit: Stochastic enters overbought territory.
    """
    _, high, low, close, _ = _extract_ohlcv(df)

    adx = _calc_adx(high, low, close, adx_period)
    k, d = _calc_stochastic(high, low, close, stoch_period, stoch_smooth)

    strong_trend = adx > adx_threshold
    k_crosses_d_up = (k > d) & (k.shift(1) <= d.shift(1))
    in_oversold = k < oversold

    entries = strong_trend & k_crosses_d_up & in_oversold
    exits = k > overbought

    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def gap_fade_signals(
    df: pd.DataFrame,
    gap_threshold: float = 0.03,
    min_gap_fill_bars: int = 5,
) -> tuple[pd.Series, pd.Series]:
    """Gap fade (mean-reversion on overnight gaps) strategy.

    For gap-up: price opens >gap_threshold above prior close.
    Entry (short/fade) when gap-up open is detected and the current bar
    closes below its own open (confirming rejection). Using daily data, we
    approximate the 'first 5-min candle break' rule by requiring the close
    to be below the open of the gap bar.

    The strategy is expressed as a long position on the SHORT side — entries
    signal the start of a fade (short), exits when price returns near the
    prior close (gap filled).
    """
    _, _, _, close, _ = _extract_ohlcv(df)
    open_s = df["open"].astype(float).reset_index(drop=True)

    prev_close = close.shift(1)
    gap_up = (open_s - prev_close) / prev_close.replace(0, np.nan) > gap_threshold
    rejection = close < open_s  # bar closes below its own open

    entries = gap_up & rejection
    gap_fill_target = prev_close
    exits = close <= gap_fill_target

    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def vrp_harvest_signals(
    df: pd.DataFrame,
    rv_window: int = 20,
    iv_proxy_window: int = 60,
    z_entry: float = -1.0,
    z_exit: float = 0.5,
) -> tuple[pd.Series, pd.Series]:
    """Volatility Risk Premium (VRP) harvest strategy.

    Since true implied volatility requires options data unavailable in a daily
    OHLCV feed, this proxy strategy uses the spread between a longer-term
    rolling-vol estimate (IV proxy) and a shorter-term realized vol estimate.

    Entry: realized vol is significantly below the IV proxy — the premium
    exists and the low-vol regime makes premium selling favorable.
    Z-score of (RV - IV_proxy) below z_entry threshold.

    Exit: spread normalizes (z-score rises above z_exit).
    """
    _, _, _, close, _ = _extract_ohlcv(df)

    log_returns = np.log(close / close.shift(1))
    rv = log_returns.rolling(rv_window).std() * np.sqrt(252)
    iv_proxy = log_returns.rolling(iv_proxy_window).std() * np.sqrt(252)

    spread = rv - iv_proxy
    spread_mean = spread.rolling(iv_proxy_window).mean()
    spread_std = spread.rolling(iv_proxy_window).std()
    z_score = (spread - spread_mean) / spread_std.replace(0, np.nan)

    entries = z_score < z_entry
    exits = z_score > z_exit

    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_STRATEGY_MAP = {
    "ma_crossover": lambda df, p: ma_crossover_signals(
        df,
        fast_window=p.get("fast_window", 10),
        slow_window=p.get("slow_window", 50),
    ),
    "mean_reversion": lambda df, p: mean_reversion_signals(
        df,
        lookback=p.get("lookback", 20),
        z_threshold=p.get("z_threshold", 2.0),
    ),
    "breakout": lambda df, p: breakout_signals(
        df,
        bb_window=p.get("bb_window", 20),
        bb_std=p.get("bb_std", 2.0),
        squeeze_lookback=p.get("squeeze_lookback", 120),
        donchian_window=p.get("donchian_window", 20),
    ),
    "trend_pullback": lambda df, p: trend_pullback_signals(
        df,
        adx_period=p.get("adx_period", 14),
        adx_threshold=p.get("adx_threshold", 25.0),
        stoch_period=p.get("stoch_period", 14),
        stoch_smooth=p.get("stoch_smooth", 3),
        oversold=p.get("oversold", 20.0),
        overbought=p.get("overbought", 80.0),
    ),
    "gap_fade": lambda df, p: gap_fade_signals(
        df,
        gap_threshold=p.get("gap_threshold", 0.03),
        min_gap_fill_bars=p.get("min_gap_fill_bars", 5),
    ),
    "vrp_harvest": lambda df, p: vrp_harvest_signals(
        df,
        rv_window=p.get("rv_window", 20),
        iv_proxy_window=p.get("iv_proxy_window", 60),
        z_entry=p.get("z_entry", -1.0),
        z_exit=p.get("z_exit", 0.5),
    ),
}


def build_signal_array(
    df: pd.DataFrame,
    strategy: str,
    params: dict,
) -> tuple[pd.Series, pd.Series]:
    """Dispatch to the correct strategy function.

    Args:
        df: OHLCV DataFrame with columns open, high, low, close, volume.
        strategy: Strategy key string.
        params: Strategy-specific parameter dict.

    Returns:
        (entries, exits) boolean Series aligned to df.index.
    """
    handler = _STRATEGY_MAP.get(strategy)
    if handler is None:
        raise ValueError(f"Unknown strategy: {strategy!r}. Valid: {sorted(_STRATEGY_MAP)}")
    return handler(df, params)
