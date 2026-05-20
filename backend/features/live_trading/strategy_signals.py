"""Compute live strategy signals by running all backtest strategies on resampled OHLCV bars."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from features.backtesting.strategies import _STRATEGY_MAP
from features.backtesting.stance import (
    _STANCE_MAP,
    build_signal_timeline_from_stance,
    compute_strategy_stance,
)
from features.backtesting.strategies.helpers import (
    _calc_adx,
    _calc_aroon,
    _calc_atr,
    _calc_ema,
    _calc_laguerre_rsi,
    _calc_macd,
    _calc_rsi,
    _calc_stoch_rsi,
    _calc_vwap,
    _extract_ohlcv,
)
from utils.logging import get_logger

logger = get_logger(__name__)

MIN_BARS_REQUIRED = 30

_STRATEGY_META: dict[str, dict[str, str]] = {
    "ma_crossover":          {"label": "MA Crossover",                       "group": "Original"},
    "mean_reversion":        {"label": "Mean Reversion",                      "group": "Original"},
    "breakout":              {"label": "Breakout (Volatility Expansion)",      "group": "Original"},
    "trend_pullback":        {"label": "Trend-Following with Pullbacks",       "group": "Original"},
    "gap_fade":              {"label": "Gap Fade",                            "group": "Original"},
    "vrp_harvest":           {"label": "VRP Harvest",                         "group": "Original"},
    "sma_cross":             {"label": "SMA Cross (Golden / Death Cross)",     "group": "Moving Average"},
    "ema_cross":             {"label": "EMA Cross",                           "group": "Moving Average"},
    "sma_break":             {"label": "Standard SMA Break (20 / 50 / 200)",  "group": "Moving Average"},
    "macd":                  {"label": "MACD",                                "group": "Momentum"},
    "rsi":                   {"label": "RSI (Relative Strength Index)",        "group": "Momentum"},
    "lrsi":                  {"label": "LRSI (Laguerre RSI)",                 "group": "Momentum"},
    "new_high_low":          {"label": "New 52-Week High / Low",              "group": "Momentum"},
    "momentum_rotation":     {"label": "Momentum Rotation",                   "group": "Momentum"},
    "aroon":                 {"label": "Aroon 52",                            "group": "Momentum"},
    "stoch_rsi":             {"label": "Stochastic RSI",                      "group": "Momentum"},
    "atr_trailing_stop":     {"label": "ATR Trailing Stop",                   "group": "Volatility"},
    "vwap_cross":            {"label": "VWAP Cross",                          "group": "Volatility"},
    "grid_trading":          {"label": "Grid Trading",                        "group": "Volatility"},
    "wedge_compression":     {"label": "Horizontal / Wedge Compression",      "group": "Volatility"},
    "mean_reversion_trend":  {"label": "Mean Reversion to Trend",             "group": "Mean Reversion"},
    "mean_reversion_range":  {"label": "Mean Reversion in Range",             "group": "Mean Reversion"},
    "reverting_market":      {"label": "Reverting Market (Sideways)",          "group": "Mean Reversion"},
    "range_breakout":        {"label": "Range Breakout",                      "group": "Breakout"},
    "orb":                   {"label": "Open Range Breakout (ORB)",            "group": "Breakout"},
    "seasonal":              {"label": "Seasonal / Sell in May",              "group": "Seasonal"},
}

_DEFAULT_PARAMS: dict[str, dict[str, float]] = {
    "ma_crossover":         {"fast_window": 10, "slow_window": 50},
    "mean_reversion":       {"lookback": 20, "z_threshold": 2.0},
    "breakout":             {"bb_window": 20, "bb_std": 2.0, "squeeze_lookback": 120, "donchian_window": 20},
    "trend_pullback":       {"adx_period": 14, "adx_threshold": 25.0, "stoch_period": 14, "stoch_smooth": 3,
                             "oversold": 20.0, "overbought": 80.0},
    "gap_fade":             {"gap_threshold": 0.03, "min_gap_fill_bars": 5},
    "vrp_harvest":          {"rv_window": 20, "iv_proxy_window": 60, "z_entry": -1.0, "z_exit": 0.5},
    "sma_cross":            {"fast_window": 50, "slow_window": 200},
    "ema_cross":            {"fast_span": 12, "slow_span": 26},
    "sma_break":            {"sma_window": 200},
    "macd":                 {"fast": 12, "slow": 26, "signal": 9},
    "rsi":                  {"period": 14, "overbought": 70.0, "oversold": 30.0},
    "lrsi":                 {"gamma": 0.5, "overbought": 0.8, "oversold": 0.2},
    "new_high_low":         {"lookback": 252},
    "momentum_rotation":    {"short_window": 20, "long_window": 60, "threshold": 0.0},
    "aroon":                {"period": 52, "threshold": 50.0},
    "stoch_rsi":            {"rsi_period": 14, "stoch_period": 14, "smooth_k": 3, "smooth_d": 3,
                             "overbought": 0.8, "oversold": 0.2},
    "atr_trailing_stop":    {"atr_period": 14, "atr_multiplier": 3.0, "trend_ma": 50},
    "vwap_cross":           {"band_pct": 0.0},
    "grid_trading":         {"grid_size": 0.02, "num_levels": 5},
    "wedge_compression":    {"atr_period": 14, "compression_lookback": 20, "compression_ratio": 0.5},
    "mean_reversion_trend": {"ma_window": 50, "z_threshold": 1.5, "adx_period": 14, "adx_threshold": 25.0},
    "mean_reversion_range": {"bb_window": 20, "bb_std": 2.0, "adx_period": 14, "adx_max": 20.0},
    "reverting_market":     {"rsi_period": 14, "rsi_upper": 60.0, "rsi_lower": 40.0, "adx_period": 14,
                             "adx_max": 20.0},
    "range_breakout":       {"lookback": 20},
    "orb":                  {"opening_bars": 6},
    "seasonal":             {"sell_month": 5, "buy_month": 11},
}


@dataclass
class StrategySignalResult:
    strategy: str
    label: str
    group: str
    signal: str  # BUY | SELL | NEUTRAL
    indicator_value: Optional[float] = None
    indicator_label: Optional[str] = None
    params: dict = field(default_factory=dict)
    signal_timeline: list[dict] = field(default_factory=list)


def _bar_time_iso(bar, index: int) -> str:
    """Extract an ISO timestamp from a bar object, or fall back to index."""
    for attr in ("bar_start", "time", "timestamp"):
        val = getattr(bar, attr, None)
        if val is None:
            continue
        if hasattr(val, "isoformat"):
            return val.isoformat()
        return str(val)
    return str(index)


def _build_dataframe(bars: list) -> pd.DataFrame:
    """Convert OHLCVBar list to a pandas DataFrame compatible with strategy functions."""
    records = [
        {
            "time": _bar_time_iso(b, i),
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        }
        for i, b in enumerate(bars)
    ]
    df = pd.DataFrame(records)
    df.columns = [c.lower() for c in df.columns]
    return df


def _determine_signal(entries: pd.Series, exits: pd.Series) -> str:
    """Derive BUY/SELL/NEUTRAL from the last entry and exit boolean values."""
    if entries.empty:
        return "NEUTRAL"
    return _determine_signal_at_index(entries, exits, len(entries) - 1)


def _determine_signal_at_index(entries: pd.Series, exits: pd.Series, index: int) -> str:
    """Derive BUY/SELL/NEUTRAL at a single bar index."""
    if entries.empty or index < 0 or index >= len(entries):
        return "NEUTRAL"
    if bool(entries.iloc[index]):
        return "BUY"
    if bool(exits.iloc[index]):
        return "SELL"
    return "NEUTRAL"


def _to_timeline_signal(signal: str) -> str:
    return {"BUY": "Buy", "SELL": "Sell", "NEUTRAL": "Neutral"}.get(signal, "Neutral")


def _stance_label_to_api_signal(stance: str) -> str:
    """Map stance chart labels (Buy/Sell/Neutral) to API signal strings."""
    normalized = stance.strip().lower()
    if normalized == "buy":
        return "BUY"
    if normalized == "sell":
        return "SELL"
    return "NEUTRAL"


def _signal_from_stance(df: pd.DataFrame, name: str, params: dict) -> str:
    """Derive the current signal from continuous stance (not cross events)."""
    stance = compute_strategy_stance(df, name, params)
    if stance.empty:
        return "NEUTRAL"
    return _stance_label_to_api_signal(str(stance.iloc[-1]))


def _build_stance_timeline(
    df: pd.DataFrame,
    name: str,
    params: dict,
    timeline_bars: int,
) -> list[dict]:
    """Build per-bar stance timeline for strategies with continuous stance."""
    stance = compute_strategy_stance(df, name, params)
    timeline = build_signal_timeline_from_stance(df, stance)
    if len(timeline) <= timeline_bars:
        return timeline
    return timeline[-timeline_bars:]


def _build_signal_timeline(
    df: pd.DataFrame,
    entries: pd.Series,
    exits: pd.Series,
    timeline_bars: int,
) -> list[dict]:
    """Build per-bar signal timeline for chart display."""
    n = len(df)
    if n == 0:
        return []
    start = max(0, n - timeline_bars)
    times = df["time"] if "time" in df.columns else pd.Series(range(n))
    timeline: list[dict] = []
    for i in range(start, n):
        sig = _determine_signal_at_index(entries, exits, i)
        timeline.append({"time": str(times.iloc[i]), "signal": _to_timeline_signal(sig)})
    return timeline


def _safe_last(series: pd.Series) -> Optional[float]:
    """Return the last finite value of a series, or None."""
    try:
        val = float(series.iloc[-1])
        import math
        return val if math.isfinite(val) else None
    except Exception:
        return None


def _compute_key_indicator(
    name: str, df: pd.DataFrame, params: dict
) -> tuple[Optional[float], Optional[str]]:
    """Return (indicator_value, indicator_label) for the most informative indicator
    of the given strategy.  Returns (None, None) when no single numeric value applies."""
    try:
        _, high, low, close, volume = _extract_ohlcv(df)

        if name == "rsi":
            period = int(params.get("period", 14))
            val = _safe_last(_calc_rsi(close, period))
            return val, "RSI"

        if name == "lrsi":
            gamma = float(params.get("gamma", 0.5))
            val = _safe_last(_calc_laguerre_rsi(close, gamma))
            return val, "LRSI"

        if name in ("macd",):
            fast = int(params.get("fast", 12))
            slow = int(params.get("slow", 26))
            sig = int(params.get("signal", 9))
            _, _, histogram = _calc_macd(close, fast, slow, sig)
            val = _safe_last(histogram)
            return val, "MACD Hist"

        if name in ("ma_crossover", "sma_cross"):
            fast_w = int(params.get("fast_window", 10 if name == "ma_crossover" else 50))
            slow_w = int(params.get("slow_window", 50 if name == "ma_crossover" else 200))
            fast_ma = _safe_last(close.rolling(fast_w).mean())
            slow_ma = _safe_last(close.rolling(slow_w).mean())
            if fast_ma is not None and slow_ma is not None and slow_ma != 0:
                return round(fast_ma - slow_ma, 4), "Fast − Slow MA"
            return None, "Fast − Slow MA"

        if name == "ema_cross":
            fast_span = int(params.get("fast_span", 12))
            slow_span = int(params.get("slow_span", 26))
            fast_ema = _safe_last(_calc_ema(close, fast_span))
            slow_ema = _safe_last(_calc_ema(close, slow_span))
            if fast_ema is not None and slow_ema is not None:
                return round(fast_ema - slow_ema, 4), "Fast − Slow EMA"
            return None, "Fast − Slow EMA"

        if name == "sma_break":
            sma_window = int(params.get("sma_window", 200))
            sma = _safe_last(close.rolling(sma_window).mean())
            price = _safe_last(close)
            if sma is not None and price is not None and sma != 0:
                return round((price - sma) / sma * 100, 2), "Price vs SMA %"
            return None, "Price vs SMA %"

        if name == "stoch_rsi":
            rsi_period = int(params.get("rsi_period", 14))
            stoch_period = int(params.get("stoch_period", 14))
            smooth_k = int(params.get("smooth_k", 3))
            smooth_d = int(params.get("smooth_d", 3))
            k, _ = _calc_stoch_rsi(close, rsi_period, stoch_period, smooth_k, smooth_d)
            return _safe_last(k), "StochRSI %K"

        if name == "aroon":
            period = int(params.get("period", 52))
            aroon_up, aroon_down = _calc_aroon(high, low, period)
            up_val = _safe_last(aroon_up)
            down_val = _safe_last(aroon_down)
            if up_val is not None and down_val is not None:
                return round(up_val - down_val, 2), "Aroon Up − Down"
            return None, "Aroon Up − Down"

        if name == "vwap_cross":
            vwap = _safe_last(_calc_vwap(high, low, close, volume))
            price = _safe_last(close)
            if vwap is not None and price is not None and vwap != 0:
                return round((price - vwap) / vwap * 100, 2), "Price vs VWAP %"
            return None, "Price vs VWAP %"

        if name in ("mean_reversion", "mean_reversion_range", "mean_reversion_trend"):
            lookback = int(params.get("lookback", params.get("bb_window", params.get("ma_window", 20))))
            rolling_mean = close.rolling(lookback).mean()
            rolling_std = close.rolling(lookback).std()
            last_price = _safe_last(close)
            last_mean = _safe_last(rolling_mean)
            last_std = _safe_last(rolling_std)
            if last_std and last_std > 0:
                return round((last_price - last_mean) / last_std, 3), "Z-Score"
            return None, "Z-Score"

        if name == "reverting_market":
            rsi_period = int(params.get("rsi_period", 14))
            val = _safe_last(_calc_rsi(close, rsi_period))
            return val, "RSI"

        if name == "atr_trailing_stop":
            atr_period = int(params.get("atr_period", 14))
            atr = _calc_atr(high, low, close, atr_period)
            return _safe_last(atr), "ATR"

        if name == "trend_pullback":
            adx_period = int(params.get("adx_period", 14))
            adx = _calc_adx(high, low, close, adx_period)
            return _safe_last(adx), "ADX"

        if name == "momentum_rotation":
            short_w = int(params.get("short_window", 20))
            long_w = int(params.get("long_window", 60))
            short_ret = _safe_last(close.pct_change(short_w))
            long_ret = _safe_last(close.pct_change(long_w))
            if short_ret is not None and long_ret is not None:
                return round(short_ret - long_ret, 5), "Short − Long Return"
            return None, "Short − Long Return"

        if name == "new_high_low":
            lookback = int(params.get("lookback", 252))
            price = _safe_last(close)
            high_val = _safe_last(close.rolling(lookback).max())
            if price is not None and high_val is not None and high_val > 0:
                return round((price / high_val - 1) * 100, 2), "% From High"
            return None, "% From High"

    except Exception as exc:
        logger.warning("indicator_compute_error", strategy=name, error=str(exc))

    return None, None


def _run_single_strategy(name: str, df: pd.DataFrame) -> str:
    """Run one strategy and return its signal string; returns NEUTRAL on any error."""
    handler = _STRATEGY_MAP.get(name)
    if handler is None:
        return "NEUTRAL"
    try:
        params = _DEFAULT_PARAMS.get(name, {})
        entries, exits = handler(df, params)
        if name in _STANCE_MAP:
            return _signal_from_stance(df, name, params)
        return _determine_signal(entries, exits)
    except Exception as exc:
        logger.warning("strategy_signal_error", strategy=name, error=str(exc))
        return "NEUTRAL"


def _run_strategy_full(
    name: str,
    df: pd.DataFrame,
    *,
    params: Optional[dict] = None,
    include_timeline: bool = False,
    timeline_bars: int = 120,
) -> tuple[str, Optional[float], Optional[str], dict, list[dict]]:
    """Run one strategy; returns signal, indicator, params, and optional timeline."""
    handler = _STRATEGY_MAP.get(name)
    base = _DEFAULT_PARAMS.get(name, {})
    merged = {**base, **(params or {})}
    if handler is None:
        return "NEUTRAL", None, None, merged, []
    try:
        entries, exits = handler(df, merged)
        if name in _STANCE_MAP:
            signal = _signal_from_stance(df, name, merged)
        else:
            signal = _determine_signal(entries, exits)
        if include_timeline:
            if name in _STANCE_MAP:
                timeline = _build_stance_timeline(df, name, merged, timeline_bars)
            else:
                timeline = _build_signal_timeline(df, entries, exits, timeline_bars)
        else:
            timeline = []
    except Exception as exc:
        logger.warning("strategy_signal_error", strategy=name, error=str(exc))
        return "NEUTRAL", None, None, merged, []

    indicator_value, indicator_label = _compute_key_indicator(name, df, merged)
    return signal, indicator_value, indicator_label, merged, timeline


def compute_strategy_signal(
    bars: list,
    strategy_name: str,
    symbol: str = "",
    params: Optional[dict] = None,
) -> Optional[str]:
    """Return latest BUY/SELL/NEUTRAL for one strategy on the given bars."""
    if len(bars) < MIN_BARS_REQUIRED:
        return None
    df = _build_dataframe(bars)
    signal, _, _, _, _ = _run_strategy_full(strategy_name, df, params=params)
    return signal


def compute_strategy_signals(
    bars: list,
    symbol: str,
    *,
    include_timeline: bool = False,
    timeline_bars: int = 120,
    strategy_names: list[str] | None = None,
) -> list[StrategySignalResult]:
    """Run backtest strategies on live OHLCV bars and return the latest signal per strategy.

    When strategy_names is set, only those strategies are evaluated.
    Returns an empty list when there are insufficient bars.
    """
    if len(bars) < MIN_BARS_REQUIRED:
        logger.warning(
            "insufficient_bars_for_strategy_signals",
            symbol=symbol,
            bars=len(bars),
            required=MIN_BARS_REQUIRED,
        )
        return []

    df = _build_dataframe(bars)
    results: list[StrategySignalResult] = []
    names = strategy_names if strategy_names else list(_STRATEGY_MAP.keys())

    for name in names:
        if name not in _STRATEGY_MAP:
            continue
        meta = _STRATEGY_META.get(name, {"label": name, "group": "Other"})
        signal, indicator_value, indicator_label, params, timeline = _run_strategy_full(
            name, df, include_timeline=include_timeline, timeline_bars=timeline_bars,
        )
        results.append(
            StrategySignalResult(
                strategy=name,
                label=meta["label"],
                group=meta["group"],
                signal=signal,
                indicator_value=indicator_value,
                indicator_label=indicator_label,
                params=params,
                signal_timeline=timeline,
            )
        )

    return results
