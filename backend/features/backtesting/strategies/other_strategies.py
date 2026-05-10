"""Miscellaneous strategy signal generators (seasonal, gap-fade, trend-pullback, VRP)."""
import numpy as np
import pandas as pd

from features.backtesting.strategies.helpers import (
    _calc_adx,
    _calc_stochastic,
    _extract_ohlcv,
    _reindex_to_df,
)


def seasonal_signals(
    df: pd.DataFrame,
    sell_month: int = 5,
    buy_month: int = 11,
) -> tuple[pd.Series, pd.Series]:
    """Seasonal / 'Sell in May' calendar strategy.

    Entry on the first bar of buy_month (default: November).
    Exit on the first bar of sell_month (default: May).

    Requires DatetimeIndex or a 'time' column with datetime values.
    """
    if "time" in df.columns:
        dates = pd.to_datetime(df["time"])
    else:
        dates = pd.Series(df.index, index=df.index)

    month = dates.dt.month.reset_index(drop=True)
    prev_month = month.shift(1)
    entries = (month == buy_month) & (prev_month != buy_month)
    exits = (month == sell_month) & (prev_month != sell_month)
    entries = entries.fillna(False).astype(bool)
    exits = exits.fillna(False).astype(bool)
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def trend_pullback_signals(
    df: pd.DataFrame,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
    stoch_period: int = 14,
    stoch_smooth: int = 3,
    oversold: float = 20.0,
    overbought: float = 80.0,
) -> tuple[pd.Series, pd.Series]:
    """Trend-following with pullback entry (ADX + Stochastic).

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
    """Gap fade (mean-reversion on overnight gaps).

    Entry when a gap-up open > gap_threshold above prior close is confirmed
    by the bar closing below its own open (rejection signal).
    Exit when price drops back to the prior close (gap filled).
    """
    _, _, _, close, _ = _extract_ohlcv(df)
    open_s = df["open"].astype(float).reset_index(drop=True)
    prev_close = close.shift(1)
    gap_up = (open_s - prev_close) / prev_close.replace(0, np.nan) > gap_threshold
    rejection = close < open_s
    entries = gap_up & rejection
    exits = close <= prev_close
    return _reindex_to_df(entries, df), _reindex_to_df(exits, df)


def vrp_harvest_signals(
    df: pd.DataFrame,
    rv_window: int = 20,
    iv_proxy_window: int = 60,
    z_entry: float = -1.0,
    z_exit: float = 0.5,
) -> tuple[pd.Series, pd.Series]:
    """Volatility Risk Premium (VRP) harvest strategy.

    Uses spread between longer-term rolling vol (IV proxy) and shorter-term
    realized vol. Entry when realized vol is significantly below IV proxy
    (z-score < z_entry). Exit when spread normalises (z-score > z_exit).
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
