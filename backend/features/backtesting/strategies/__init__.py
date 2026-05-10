"""Strategy signal dispatcher — maps strategy names to signal generator functions.

All strategy modules expose pure functions with signature:
    (df: pd.DataFrame, **params) -> tuple[pd.Series, pd.Series]

Public surface: build_signal_array, _STRATEGY_MAP, and all individual signal functions.
"""
import pandas as pd

from features.backtesting.strategies.breakout_strategies import (
    breakout_signals,
    orb_signals,
    range_breakout_signals,
)
from features.backtesting.strategies.ma_strategies import (
    ema_cross_signals,
    ma_crossover_signals,
    sma_break_signals,
    sma_cross_signals,
)
from features.backtesting.strategies.mean_reversion_strategies import (
    mean_reversion_range_signals,
    mean_reversion_signals,
    mean_reversion_trend_signals,
    reverting_market_signals,
)
from features.backtesting.strategies.momentum_strategies import (
    lrsi_signals,
    macd_signals,
    momentum_rotation_signals,
    new_high_low_signals,
    rsi_signals,
)
from features.backtesting.strategies.other_strategies import (
    gap_fade_signals,
    seasonal_signals,
    trend_pullback_signals,
    vrp_harvest_signals,
)
from features.backtesting.strategies.volatility_strategies import (
    atr_trailing_stop_signals,
    grid_trading_signals,
    vwap_cross_signals,
    wedge_compression_signals,
)

__all__ = [
    "build_signal_array",
    "_STRATEGY_MAP",
    # MA / EMA
    "ma_crossover_signals",
    "sma_cross_signals",
    "ema_cross_signals",
    "sma_break_signals",
    # Momentum
    "macd_signals",
    "rsi_signals",
    "lrsi_signals",
    "new_high_low_signals",
    "momentum_rotation_signals",
    # Volatility
    "atr_trailing_stop_signals",
    "vwap_cross_signals",
    "grid_trading_signals",
    "wedge_compression_signals",
    # Mean reversion
    "mean_reversion_signals",
    "mean_reversion_trend_signals",
    "mean_reversion_range_signals",
    "reverting_market_signals",
    # Breakout
    "breakout_signals",
    "range_breakout_signals",
    "orb_signals",
    # Other
    "seasonal_signals",
    "trend_pullback_signals",
    "gap_fade_signals",
    "vrp_harvest_signals",
]

_STRATEGY_MAP: dict = {
    # ---- Original strategies ------------------------------------------------
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
    # ---- MA / EMA strategies ------------------------------------------------
    "sma_cross": lambda df, p: sma_cross_signals(
        df,
        fast_window=p.get("fast_window", 50),
        slow_window=p.get("slow_window", 200),
    ),
    "ema_cross": lambda df, p: ema_cross_signals(
        df,
        fast_span=p.get("fast_span", 12),
        slow_span=p.get("slow_span", 26),
    ),
    "sma_break": lambda df, p: sma_break_signals(
        df,
        sma_window=p.get("sma_window", 200),
    ),
    # ---- Momentum strategies -------------------------------------------------
    "macd": lambda df, p: macd_signals(
        df,
        fast=p.get("fast", 12),
        slow=p.get("slow", 26),
        signal=p.get("signal", 9),
    ),
    "rsi": lambda df, p: rsi_signals(
        df,
        period=p.get("period", 14),
        overbought=p.get("overbought", 70.0),
        oversold=p.get("oversold", 30.0),
    ),
    "lrsi": lambda df, p: lrsi_signals(
        df,
        gamma=p.get("gamma", 0.5),
        overbought=p.get("overbought", 0.8),
        oversold=p.get("oversold", 0.2),
    ),
    "new_high_low": lambda df, p: new_high_low_signals(
        df,
        lookback=p.get("lookback", 252),
    ),
    "momentum_rotation": lambda df, p: momentum_rotation_signals(
        df,
        short_window=p.get("short_window", 20),
        long_window=p.get("long_window", 60),
        threshold=p.get("threshold", 0.0),
    ),
    # ---- Volatility / price-level strategies ---------------------------------
    "atr_trailing_stop": lambda df, p: atr_trailing_stop_signals(
        df,
        atr_period=p.get("atr_period", 14),
        atr_multiplier=p.get("atr_multiplier", 3.0),
        trend_ma=p.get("trend_ma", 50),
    ),
    "vwap_cross": lambda df, p: vwap_cross_signals(
        df,
        band_pct=p.get("band_pct", 0.0),
    ),
    "grid_trading": lambda df, p: grid_trading_signals(
        df,
        grid_size=p.get("grid_size", 0.02),
        num_levels=p.get("num_levels", 5),
    ),
    "wedge_compression": lambda df, p: wedge_compression_signals(
        df,
        atr_period=p.get("atr_period", 14),
        compression_lookback=p.get("compression_lookback", 20),
        compression_ratio=p.get("compression_ratio", 0.5),
    ),
    # ---- Mean reversion strategies -------------------------------------------
    "mean_reversion_trend": lambda df, p: mean_reversion_trend_signals(
        df,
        ma_window=p.get("ma_window", 50),
        z_threshold=p.get("z_threshold", 1.5),
        adx_period=p.get("adx_period", 14),
        adx_threshold=p.get("adx_threshold", 25.0),
    ),
    "mean_reversion_range": lambda df, p: mean_reversion_range_signals(
        df,
        bb_window=p.get("bb_window", 20),
        bb_std=p.get("bb_std", 2.0),
        adx_period=p.get("adx_period", 14),
        adx_max=p.get("adx_max", 20.0),
    ),
    "reverting_market": lambda df, p: reverting_market_signals(
        df,
        rsi_period=p.get("rsi_period", 14),
        rsi_upper=p.get("rsi_upper", 60.0),
        rsi_lower=p.get("rsi_lower", 40.0),
        adx_period=p.get("adx_period", 14),
        adx_max=p.get("adx_max", 20.0),
    ),
    # ---- Breakout strategies -------------------------------------------------
    "range_breakout": lambda df, p: range_breakout_signals(
        df,
        lookback=p.get("lookback", 20),
    ),
    "orb": lambda df, p: orb_signals(
        df,
        opening_bars=p.get("opening_bars", 6),
    ),
    # ---- Seasonal strategies -------------------------------------------------
    "seasonal": lambda df, p: seasonal_signals(
        df,
        sell_month=p.get("sell_month", 5),
        buy_month=p.get("buy_month", 11),
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
        raise ValueError(
            f"Unknown strategy: {strategy!r}. Valid: {sorted(_STRATEGY_MAP)}"
        )
    return handler(df, params)
