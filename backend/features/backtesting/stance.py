"""Per-bar Buy / Neutral / Sell stance for combo timeline and combination."""
import numpy as np
import pandas as pd

from features.backtesting.strategies import build_signal_array
from features.backtesting.strategies.helpers import (
    _calc_adx,
    _calc_aroon,
    _calc_ema,
    _calc_laguerre_rsi,
    _calc_macd,
    _calc_rsi,
    _calc_stoch_rsi,
    _calc_stochastic,
    _calc_vwap,
    _extract_ohlcv,
    _reindex_to_df,
)

STANCE_BUY = "Buy"
STANCE_NEUTRAL = "Neutral"
STANCE_SELL = "Sell"


def _zone_stance(values: pd.Series, oversold: float, overbought: float) -> pd.Series:
    """Buy strictly below oversold; Sell strictly above overbought; else Neutral."""
    out = pd.Series(STANCE_NEUTRAL, index=values.index, dtype=object)
    out[values < oversold] = STANCE_BUY
    out[values > overbought] = STANCE_SELL
    return out


def _directional_stance(bullish: pd.Series) -> pd.Series:
    out = pd.Series(STANCE_SELL, index=bullish.index, dtype=object)
    out[bullish.fillna(False)] = STANCE_BUY
    return out


def _align_stance(stance: pd.Series, df: pd.DataFrame) -> pd.Series:
    aligned = stance.reset_index(drop=True).iloc[: len(df)]
    aligned.index = df.index
    return aligned.astype(str)


def _position_fallback_stance(
    df: pd.DataFrame, strategy: str, params: dict, flat_label: str
) -> pd.Series:
    entries, exits = build_signal_array(df, strategy, params)
    transitions = entries.astype(int) - exits.astype(int)
    last = transitions.replace(0, float("nan")).ffill().fillna(0)
    in_pos = (last > 0).astype(bool)
    stance = pd.Series(flat_label, index=in_pos.index, dtype=object)
    stance[in_pos] = STANCE_BUY
    return _align_stance(stance, df)


def _rsi_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, _, _, close, _ = _extract_ohlcv(df)
    rsi = _calc_rsi(close, p.get("period", 14))
    return _align_stance(
        _zone_stance(rsi, p.get("oversold", 30.0), p.get("overbought", 70.0)), df
    )


def _lrsi_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, _, _, close, _ = _extract_ohlcv(df)
    lrsi = _calc_laguerre_rsi(close, p.get("gamma", 0.5))
    return _align_stance(
        _zone_stance(lrsi, p.get("oversold", 0.2), p.get("overbought", 0.8)), df
    )


def _stoch_rsi_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, _, _, close, _ = _extract_ohlcv(df)
    k, _ = _calc_stoch_rsi(
        close,
        p.get("rsi_period", 14),
        p.get("stoch_period", 14),
        p.get("smooth_k", 3),
        p.get("smooth_d", 3),
    )
    return _align_stance(
        _zone_stance(k, p.get("oversold", 0.2), p.get("overbought", 0.8)), df
    )


def _macd_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, _, _, close, _ = _extract_ohlcv(df)
    macd_line, signal_line, _ = _calc_macd(
        close, p.get("fast", 12), p.get("slow", 26), p.get("signal", 9)
    )
    return _align_stance(_directional_stance(macd_line > signal_line), df)


def _ma_cross_stance(df: pd.DataFrame, fast_key: str, slow_key: str, p: dict) -> pd.Series:
    _, _, _, close, _ = _extract_ohlcv(df)
    if fast_key == "fast_span":
        fast = _calc_ema(close, p.get("fast_span", 12))
        slow = _calc_ema(close, p.get("slow_span", 26))
    else:
        fw = p.get(fast_key, 10)
        sw = p.get(slow_key, 50)
        fast = close.rolling(fw).mean()
        slow = close.rolling(sw).mean()
    return _align_stance(_directional_stance(fast > slow), df)


def _sma_break_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, _, _, close, _ = _extract_ohlcv(df)
    sma = close.rolling(p.get("sma_window", 200)).mean()
    return _align_stance(_directional_stance(close > sma), df)


def _aroon_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, high, low, _, _ = _extract_ohlcv(df)
    up, down = _calc_aroon(high, low, p.get("period", 52))
    return _align_stance(_directional_stance(up > down), df)


def _momentum_rotation_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, _, _, close, _ = _extract_ohlcv(df)
    short_ret = close.pct_change(p.get("short_window", 20))
    long_ret = close.pct_change(p.get("long_window", 60))
    thresh = p.get("threshold", 0.0)
    return _align_stance(_directional_stance(short_ret > (long_ret + thresh)), df)


def _new_high_low_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, _, _, close, _ = _extract_ohlcv(df)
    lb = p.get("lookback", 252)
    rh = close.rolling(lb).max()
    rl = close.rolling(lb).min()
    out = pd.Series(STANCE_NEUTRAL, index=close.index, dtype=object)
    out[close >= rh] = STANCE_BUY
    out[close <= rl] = STANCE_SELL
    return _align_stance(out, df)


def _vwap_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, high, low, close, volume = _extract_ohlcv(df)
    vwap = _calc_vwap(high, low, close, volume)
    return _align_stance(_directional_stance(close > vwap), df)


def _reverting_market_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, _, _, close, _ = _extract_ohlcv(df)
    rsi = _calc_rsi(close, p.get("rsi_period", 14))
    return _align_stance(
        _zone_stance(rsi, p.get("rsi_lower", 40.0), p.get("rsi_upper", 60.0)), df
    )


def _trend_pullback_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, high, low, close, _ = _extract_ohlcv(df)
    k, _ = _calc_stochastic(high, low, close, p.get("stoch_period", 14), p.get("stoch_smooth", 3))
    return _align_stance(
        _zone_stance(k, p.get("oversold", 20.0), p.get("overbought", 80.0)), df
    )


def _z_score_stance(
    df: pd.DataFrame, window_key: str, z_key: str, p: dict, default_window: int
) -> pd.Series:
    _, _, _, close, _ = _extract_ohlcv(df)
    w = p.get(window_key, default_window)
    mean = close.rolling(w).mean()
    std = close.rolling(w).std()
    z = (close - mean) / std.replace(0, np.nan)
    zt = p.get(z_key, 2.0)
    out = pd.Series(STANCE_NEUTRAL, index=close.index, dtype=object)
    out[z < -zt] = STANCE_BUY
    out[z > zt] = STANCE_SELL
    return _align_stance(out, df)


def _mean_reversion_range_stance(df: pd.DataFrame, p: dict) -> pd.Series:
    _, _, _, close, _ = _extract_ohlcv(df)
    w = p.get("bb_window", 20)
    std_mult = p.get("bb_std", 2.0)
    mid = close.rolling(w).mean()
    std = close.rolling(w).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    out = pd.Series(STANCE_NEUTRAL, index=close.index, dtype=object)
    out[close < lower] = STANCE_BUY
    out[close > upper] = STANCE_SELL
    return _align_stance(out, df)


_STANCE_MAP: dict = {
    "rsi": _rsi_stance,
    "lrsi": _lrsi_stance,
    "stoch_rsi": _stoch_rsi_stance,
    "macd": _macd_stance,
    "ma_crossover": lambda df, p: _ma_cross_stance(df, "fast_window", "slow_window", p),
    "sma_cross": lambda df, p: _ma_cross_stance(df, "fast_window", "slow_window", p),
    "ema_cross": lambda df, p: _ma_cross_stance(df, "fast_span", "slow_span", p),
    "sma_break": _sma_break_stance,
    "aroon": _aroon_stance,
    "momentum_rotation": _momentum_rotation_stance,
    "new_high_low": _new_high_low_stance,
    "vwap_cross": _vwap_stance,
    "reverting_market": _reverting_market_stance,
    "trend_pullback": _trend_pullback_stance,
    "mean_reversion": lambda df, p: _z_score_stance(df, "lookback", "z_threshold", p, 20),
    "mean_reversion_trend": lambda df, p: _z_score_stance(df, "ma_window", "z_threshold", p, 50),
    "mean_reversion_range": _mean_reversion_range_stance,
}

_POSITION_FALLBACK_NEUTRAL = frozenset({
    "vrp_harvest",
    "grid_trading",
})


def compute_strategy_stance(
    df: pd.DataFrame,
    strategy: str,
    params: dict | None = None,
) -> pd.Series:
    """Return per-bar stance labels aligned to df rows."""
    p = params or {}
    handler = _STANCE_MAP.get(strategy)
    if handler is not None:
        return handler(df, p)
    flat = STANCE_NEUTRAL if strategy in _POSITION_FALLBACK_NEUTRAL else STANCE_SELL
    return _position_fallback_stance(df, strategy, p, flat)


def build_signal_timeline_from_stance(
    df: pd.DataFrame,
    stance: pd.Series,
) -> list[dict]:
    time_index = df["time"] if "time" in df.columns else df.index
    return [
        {"time": str(t), "signal": str(stance.iloc[i])}
        for i, t in enumerate(time_index)
    ]


def _vote_and(stances: list[str]) -> str | None:
    if all(s == STANCE_BUY for s in stances):
        return "long"
    if all(s == STANCE_SELL for s in stances):
        return "flat"
    return None


def _vote_majority(stances: list[str]) -> str | None:
    buys = sum(1 for s in stances if s == STANCE_BUY)
    sells = sum(1 for s in stances if s == STANCE_SELL)
    if buys > sells:
        return "long"
    if sells > buys:
        return "flat"
    return None


def _vote_or(stances: list[str]) -> str | None:
    """OR / Any: any Sell exits; any Buy enters; Sell wins on mixed bars."""
    if any(s == STANCE_SELL for s in stances):
        return "flat"
    if any(s == STANCE_BUY for s in stances):
        return "long"
    return None


def _vote_weighted(
    stances: list[str], weights: list[float], threshold: float
) -> str | None:
    w_buy = sum(w for s, w in zip(stances, weights) if s == STANCE_BUY)
    w_sell = sum(w for s, w in zip(stances, weights) if s == STANCE_SELL)
    if w_buy == 0 and w_sell == 0:
        return None
    if w_sell == 0:
        return "long"
    if w_buy == 0:
        return "flat"
    total = w_buy + w_sell
    ratio = w_buy / total
    if ratio > threshold:
        return "long"
    if ratio < (1.0 - threshold):
        return "flat"
    return None


def _decide_bar_target(
    stances: list[str],
    mode: str,
    weights: list[float],
    threshold: float,
) -> str | None:
    if mode == "and":
        return _vote_and(stances)
    if mode in ("or", "any"):
        return _vote_or(stances)
    if mode == "majority":
        return _vote_majority(stances)
    if mode == "weighted":
        return _vote_weighted(stances, weights, threshold)
    raise ValueError(f"Unknown combination mode: {mode!r}")


def combine_stances(
    stance_list: list[pd.Series],
    mode: str,
    weights: list[float],
    threshold: float = 0.5,
) -> pd.Series:
    """Combine per-strategy stance series into a boolean long-position series.

    Neutral legs abstain. Tie or no actionable vote holds the prior position.
    """
    if not stance_list:
        raise ValueError("stance_list must not be empty")
    if mode == "weighted" and sum(weights) == 0:
        raise ValueError("Sum of weights must be > 0")

    n = len(stance_list[0])
    index = stance_list[0].index
    combined = pd.Series(False, index=index, dtype=bool)
    prev = False
    for i in range(n):
        bar_stances = [str(s.iloc[i]) for s in stance_list]
        target = _decide_bar_target(bar_stances, mode, weights, threshold)
        if target == "long":
            prev = True
        elif target == "flat":
            prev = False
        combined.iloc[i] = prev
    return combined
