"""Compute live strategy signals by running all backtest strategies on resampled OHLCV bars."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from features.backtesting.strategies import _STRATEGY_MAP
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


def _build_dataframe(bars: list) -> pd.DataFrame:
    """Convert OHLCVBar list to a pandas DataFrame compatible with strategy functions."""
    records = [
        {
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        }
        for b in bars
    ]
    df = pd.DataFrame(records)
    df.columns = [c.lower() for c in df.columns]
    return df


def _determine_signal(entries: pd.Series, exits: pd.Series) -> str:
    """Derive BUY/SELL/NEUTRAL from the last entry and exit boolean values."""
    last_entry = bool(entries.iloc[-1]) if not entries.empty else False
    last_exit = bool(exits.iloc[-1]) if not exits.empty else False
    if last_entry:
        return "BUY"
    if last_exit:
        return "SELL"
    return "NEUTRAL"


def _run_single_strategy(name: str, df: pd.DataFrame) -> str:
    """Run one strategy and return its signal string; returns NEUTRAL on any error."""
    handler = _STRATEGY_MAP.get(name)
    if handler is None:
        return "NEUTRAL"
    try:
        params = _DEFAULT_PARAMS.get(name, {})
        entries, exits = handler(df, params)
        return _determine_signal(entries, exits)
    except Exception as exc:
        logger.warning("strategy_signal_error", strategy=name, error=str(exc))
        return "NEUTRAL"


def compute_strategy_signals(bars: list, symbol: str) -> list[StrategySignalResult]:
    """Run all backtest strategies on live OHLCV bars and return the latest signal per strategy.

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

    for name in _STRATEGY_MAP:
        meta = _STRATEGY_META.get(name, {"label": name, "group": "Other"})
        signal = _run_single_strategy(name, df)
        results.append(
            StrategySignalResult(
                strategy=name,
                label=meta["label"],
                group=meta["group"],
                signal=signal,
            )
        )

    return results
