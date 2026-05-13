"""Per-strategy indicator computation functions and dispatch map.

Each function takes a DataFrame (OHLCV) and a params dict, and returns a
DataFrame whose columns are the named indicator series for that strategy.

Extracted into this module to avoid circular imports between runner.py,
combo_runner.py, and indicator_snapshot.py.
"""
import numpy as np
import pandas as pd
from typing import Callable

from features.backtesting.strategies.helpers import (
    _calc_adx,
    _calc_aroon,
    _calc_atr,
    _calc_ema,
    _calc_laguerre_rsi,
    _calc_macd,
    _calc_rsi,
    _calc_stoch_rsi,
    _calc_stochastic,
    _calc_vwap,
    _extract_ohlcv,
)


def _ma_crossover_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    return pd.DataFrame({
        "fast_ma": close.rolling(p.get("fast_window", 10)).mean(),
        "slow_ma": close.rolling(p.get("slow_window", 50)).mean(),
    })


def _sma_cross_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    return pd.DataFrame({
        "fast_sma": close.rolling(p.get("fast_window", 50)).mean(),
        "slow_sma": close.rolling(p.get("slow_window", 200)).mean(),
    })


def _ema_cross_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    return pd.DataFrame({
        "fast_ema": _calc_ema(close, p.get("fast_span", 12)),
        "slow_ema": _calc_ema(close, p.get("slow_span", 26)),
    })


def _sma_break_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    return pd.DataFrame({"sma": close.rolling(p.get("sma_window", 200)).mean()})


def _macd_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    macd_line, signal_line, _ = _calc_macd(
        close, p.get("fast", 12), p.get("slow", 26), p.get("signal", 9)
    )
    return pd.DataFrame({"macd": macd_line, "signal": signal_line})


def _rsi_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    return pd.DataFrame({"rsi": _calc_rsi(close, p.get("period", 14))})


def _lrsi_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    return pd.DataFrame({"lrsi": _calc_laguerre_rsi(close, p.get("gamma", 0.5))})


def _new_high_low_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    lookback = p.get("lookback", 252)
    return pd.DataFrame({
        "period_high": close.rolling(lookback).max(),
        "period_low": close.rolling(lookback).min(),
    })


def _aroon_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, high, low, _, _ = _extract_ohlcv(df)
    aroon_up, aroon_down = _calc_aroon(high, low, p.get("period", 52))
    return pd.DataFrame({"aroon_up": aroon_up, "aroon_down": aroon_down})


def _stoch_rsi_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    k, d = _calc_stoch_rsi(
        close,
        p.get("rsi_period", 14), p.get("stoch_period", 14),
        p.get("smooth_k", 3), p.get("smooth_d", 3),
    )
    return pd.DataFrame({"stoch_k": k, "stoch_d": d})


def _momentum_rotation_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    short_ret = close.pct_change(p.get("short_window", 20)) * 100
    long_ret = close.pct_change(p.get("long_window", 60)) * 100
    return pd.DataFrame({"short_ret_pct": short_ret, "long_ret_pct": long_ret})


def _atr_trailing_stop_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, high, low, close, _ = _extract_ohlcv(df)
    atr = _calc_atr(high, low, close, p.get("atr_period", 14))
    trend = close.rolling(p.get("trend_ma", 50)).mean()
    return pd.DataFrame({"atr": atr, "trend_ma": trend})


def _vwap_cross_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, high, low, close, volume = _extract_ohlcv(df)
    return pd.DataFrame({"vwap": _calc_vwap(high, low, close, volume)})


def _grid_trading_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    grid_size = p.get("grid_size", 0.02)
    num_levels = p.get("num_levels", 5)
    baseline = close.rolling(num_levels * 10).mean()
    return pd.DataFrame({
        "baseline": baseline,
        "lower_grid": baseline * (1 - grid_size * num_levels),
        "upper_grid": baseline * (1 + grid_size * num_levels),
    })


def _wedge_compression_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, high, low, close, _ = _extract_ohlcv(df)
    atr = _calc_atr(high, low, close, p.get("atr_period", 14))
    lookback = p.get("compression_lookback", 20)
    return pd.DataFrame({"atr": atr, "atr_mean": atr.rolling(lookback).mean()})


def _mean_reversion_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    lookback = p.get("lookback", 20)
    rolling_mean = close.rolling(lookback).mean()
    rolling_std = close.rolling(lookback).std()
    z = (close - rolling_mean) / rolling_std.replace(0, np.nan)
    return pd.DataFrame({"z_score": z})


def _mean_reversion_trend_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, high, low, close, _ = _extract_ohlcv(df)
    rolling_mean = close.rolling(p.get("ma_window", 50)).mean()
    rolling_std = close.rolling(p.get("ma_window", 50)).std()
    z = (close - rolling_mean) / rolling_std.replace(0, np.nan)
    adx = _calc_adx(high, low, close, p.get("adx_period", 14))
    return pd.DataFrame({"z_score": z, "adx": adx})


def _mean_reversion_range_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, high, low, close, _ = _extract_ohlcv(df)
    bb_window = p.get("bb_window", 20)
    bb_mid = close.rolling(bb_window).mean()
    bb_std_s = close.rolling(bb_window).std()
    bb_pct = (close - bb_mid) / bb_std_s.replace(0, np.nan)
    adx = _calc_adx(high, low, close, p.get("adx_period", 14))
    return pd.DataFrame({"bb_pct": bb_pct, "adx": adx})


def _reverting_market_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, high, low, close, _ = _extract_ohlcv(df)
    rsi = _calc_rsi(close, p.get("rsi_period", 14))
    adx = _calc_adx(high, low, close, p.get("adx_period", 14))
    return pd.DataFrame({"rsi": rsi, "adx": adx})


def _breakout_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, high, low, close, _ = _extract_ohlcv(df)
    bb_window = p.get("bb_window", 20)
    bb_mid = close.rolling(bb_window).mean()
    bb_band = close.rolling(bb_window).std() * p.get("bb_std", 2.0)
    donchian_window = p.get("donchian_window", 20)
    return pd.DataFrame({
        "bb_upper": bb_mid + bb_band,
        "bb_lower": bb_mid - bb_band,
        "donchian_high": high.rolling(donchian_window).max(),
        "donchian_low": low.rolling(donchian_window).min(),
    })


def _range_breakout_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, high, low, _, _ = _extract_ohlcv(df)
    lookback = p.get("lookback", 20)
    return pd.DataFrame({
        "range_high": high.rolling(lookback).max(),
        "range_low": low.rolling(lookback).min(),
    })


def _trend_pullback_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, high, low, close, _ = _extract_ohlcv(df)
    adx = _calc_adx(high, low, close, p.get("adx_period", 14))
    k, _ = _calc_stochastic(high, low, close, p.get("stoch_period", 14), p.get("stoch_smooth", 3))
    return pd.DataFrame({"adx": adx, "stoch_k": k})


def _vrp_harvest_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    _, _, _, close, _ = _extract_ohlcv(df)
    rv_window = p.get("rv_window", 20)
    iv_window = p.get("iv_proxy_window", 60)
    log_ret = np.log(close / close.shift(1))
    rv = log_ret.rolling(rv_window).std() * np.sqrt(252)
    iv_proxy = log_ret.rolling(iv_window).std() * np.sqrt(252)
    spread = rv - iv_proxy
    spread_std = spread.rolling(iv_window).std()
    vrp_z = (spread - spread.rolling(iv_window).mean()) / spread_std.replace(0, np.nan)
    return pd.DataFrame({"vrp_z": vrp_z, "rv": rv, "iv_proxy": iv_proxy})


def _empty_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    """Placeholder for strategies without meaningful continuous indicators."""
    return pd.DataFrame(index=range(len(df)))


INDICATOR_MAP: dict[str, Callable] = {
    "ma_crossover": _ma_crossover_indicators,
    "mean_reversion": _mean_reversion_indicators,
    "breakout": _breakout_indicators,
    "trend_pullback": _trend_pullback_indicators,
    "gap_fade": _empty_indicators,
    "vrp_harvest": _vrp_harvest_indicators,
    "sma_cross": _sma_cross_indicators,
    "ema_cross": _ema_cross_indicators,
    "sma_break": _sma_break_indicators,
    "macd": _macd_indicators,
    "rsi": _rsi_indicators,
    "lrsi": _lrsi_indicators,
    "new_high_low": _new_high_low_indicators,
    "momentum_rotation": _momentum_rotation_indicators,
    "aroon": _aroon_indicators,
    "stoch_rsi": _stoch_rsi_indicators,
    "atr_trailing_stop": _atr_trailing_stop_indicators,
    "vwap_cross": _vwap_cross_indicators,
    "grid_trading": _grid_trading_indicators,
    "wedge_compression": _wedge_compression_indicators,
    "mean_reversion_trend": _mean_reversion_trend_indicators,
    "mean_reversion_range": _mean_reversion_range_indicators,
    "reverting_market": _reverting_market_indicators,
    "range_breakout": _range_breakout_indicators,
    "orb": _empty_indicators,
    "seasonal": _empty_indicators,
}
