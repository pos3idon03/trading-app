"""Shared OHLCV extraction and indicator helper functions for all strategy modules."""
import numpy as np
import pandas as pd


def _extract_ohlcv(
    df: pd.DataFrame,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """Return (open, high, low, close, volume) Series from a standardised OHLCV DataFrame."""
    o = df["open"].astype(float).reset_index(drop=True)
    h = df["high"].astype(float).reset_index(drop=True)
    lo = df["low"].astype(float).reset_index(drop=True)
    c = df["close"].astype(float).reset_index(drop=True)
    v = (
        df["volume"].astype(float).reset_index(drop=True)
        if "volume" in df.columns
        else pd.Series(0.0, index=c.index)
    )
    return o, h, lo, c, v


def _reindex_to_df(series: pd.Series, df: pd.DataFrame) -> pd.Series:
    """Restore the original DataFrame index on a computed signal series."""
    series = series.reset_index(drop=True)
    series.index = df.index
    return series


# ---------------------------------------------------------------------------
# Shared indicator helpers
# ---------------------------------------------------------------------------


def _calc_ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=span, adjust=False).mean()


def _calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _compute_atr_trailing_stop_state(
    close: pd.Series,
    atr: pd.Series,
    trend: pd.Series,
    atr_multiplier: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bar-by-bar ATR trailing stop with upward-only stop ratcheting."""
    n = len(close)
    close_vals = close.to_numpy(dtype=float, copy=False)
    atr_vals = atr.to_numpy(dtype=float, copy=False)
    above_trend = (close > trend).to_numpy(dtype=bool, copy=False)

    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    stop_levels = np.full(n, np.nan, dtype=float)

    in_position = False
    trailing_stop = np.nan

    for i in range(1, n):
        if not in_position:
            if above_trend[i] and not above_trend[i - 1]:
                candidate = close_vals[i] - atr_multiplier * atr_vals[i]
                if not np.isfinite(candidate):
                    continue
                in_position = True
                trailing_stop = candidate
                entries[i] = True
                stop_levels[i] = trailing_stop
            continue

        candidate = close_vals[i] - atr_multiplier * atr_vals[i]
        if np.isfinite(candidate):
            trailing_stop = max(trailing_stop, candidate)
        stop_levels[i] = trailing_stop

        if close_vals[i] < trailing_stop:
            exits[i] = True
            in_position = False
            trailing_stop = np.nan

    return entries, exits, stop_levels


def _calc_adx(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """Average Directional Index."""
    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)

    dm_plus = np.where(
        (high - high.shift(1)) > (low.shift(1) - low), high - high.shift(1), 0.0
    )
    dm_minus = np.where(
        (low.shift(1) - low) > (high - high.shift(1)), low.shift(1) - low, 0.0
    )
    dm_plus = pd.Series(np.where(np.array(dm_plus) > 0, dm_plus, 0.0), index=high.index)
    dm_minus = pd.Series(np.where(np.array(dm_minus) > 0, dm_minus, 0.0), index=high.index)

    atr = tr.ewm(span=period, adjust=False).mean()
    di_plus = 100 * dm_plus.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)
    di_minus = 100 * dm_minus.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)

    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    return dx.ewm(span=period, adjust=False).mean()


def _calc_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
    smooth: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """Stochastic oscillator %K and %D."""
    lowest_low = low.rolling(period).min()
    highest_high = high.rolling(period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(smooth).mean()
    return k, d


def _calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _calc_macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line, histogram."""
    ema_fast = _calc_ema(close, fast)
    ema_slow = _calc_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _calc_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _calc_laguerre_rsi(close: pd.Series, gamma: float = 0.5) -> pd.Series:
    """Laguerre RSI — a smoother RSI variant using a 4-element Laguerre filter."""
    n = len(close)
    l0 = np.zeros(n)
    l1 = np.zeros(n)
    l2 = np.zeros(n)
    l3 = np.zeros(n)
    c = close.values

    for i in range(1, n):
        l0[i] = (1 - gamma) * c[i] + gamma * l0[i - 1]
        l1[i] = -gamma * l0[i] + l0[i - 1] + gamma * l1[i - 1]
        l2[i] = -gamma * l1[i] + l1[i - 1] + gamma * l2[i - 1]
        l3[i] = -gamma * l2[i] + l2[i - 1] + gamma * l3[i - 1]

    cu = np.where(l0 >= l1, l0 - l1, 0.0) + np.where(l1 >= l2, l1 - l2, 0.0) + np.where(l2 >= l3, l2 - l3, 0.0)
    cd = np.where(l0 < l1, l1 - l0, 0.0) + np.where(l1 < l2, l2 - l1, 0.0) + np.where(l2 < l3, l3 - l2, 0.0)

    total = cu + cd
    lrsi = np.where(total == 0, 0.0, cu / total)
    return pd.Series(lrsi, index=close.index)


def _calc_vwap(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
) -> pd.Series:
    """Cumulative VWAP from start of series."""
    typical_price = (high + low + close) / 3.0
    cum_tp_vol = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


def _calc_aroon(
    high: pd.Series,
    low: pd.Series,
    period: int = 52,
) -> tuple[pd.Series, pd.Series]:
    """Aroon Up and Aroon Down oscillators.

    Aroon Up  = 100 * (bars since period high) / period
    Aroon Down = 100 * (bars since period low)  / period
    Both range 0–100.
    """
    rolling_high_idx = high.rolling(period + 1).apply(np.argmax, raw=True)
    rolling_low_idx = low.rolling(period + 1).apply(np.argmin, raw=True)
    aroon_up = (rolling_high_idx / period) * 100
    aroon_down = (rolling_low_idx / period) * 100
    return aroon_up, aroon_down


def _calc_stoch_rsi(
    close: pd.Series,
    rsi_period: int = 14,
    stoch_period: int = 14,
    smooth_k: int = 3,
    smooth_d: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """Stochastic RSI %K and %D lines (range 0–1).

    Applies the stochastic formula to RSI values for a more sensitive oscillator.
    """
    rsi = _calc_rsi(close, rsi_period)
    lowest_rsi = rsi.rolling(stoch_period).min()
    highest_rsi = rsi.rolling(stoch_period).max()
    rsi_range = (highest_rsi - lowest_rsi).replace(0, np.nan)
    raw_k = (rsi - lowest_rsi) / rsi_range
    k = raw_k.rolling(smooth_k).mean()
    d = k.rolling(smooth_d).mean()
    return k, d
