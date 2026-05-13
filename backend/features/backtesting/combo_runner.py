"""Multi-strategy combination backtest runner.

Signal combination works on *position state* (is each strategy currently long?)
rather than raw entry/exit bars.  This means:
  - AND mode: combined enters when ALL strategies are simultaneously long.
  - Majority mode: combined enters when >50% of strategies are long.
  - Weighted mode: combined enters when the weighted fraction exceeds threshold.

Converting to position state first ensures that if strategy A entered on bar 50
and strategy B enters on bar 73 (both still in position), the combo triggers a
buy on bar 73 — which is the expected behaviour.
"""
import time
from dataclasses import dataclass

import pandas as pd

from features.backtesting.metrics import compile_all_metrics
from features.backtesting.runner import (
    BacktestResult,
    _TIMEFRAME_TO_VBT_FREQ,
    _compute_buy_hold_curve,
    _extract_trades,
)
from features.backtesting.strategies import build_signal_array
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ComboStrategyConfig:
    strategy_name: str
    strategy_params: dict
    weight: float = 1.0


# ---------------------------------------------------------------------------
# Position-state helpers
# ---------------------------------------------------------------------------

def _signals_to_position(entries: pd.Series, exits: pd.Series) -> pd.Series:
    """Convert entry/exit signal bars to a continuous boolean position state.

    On each bar the strategy is considered *in position* if the last transition
    was an entry rather than an exit.  Simultaneous entry+exit defaults to out.
    """
    transitions = entries.astype(int) - exits.astype(int)
    last_signal = transitions.replace(0, float("nan")).ffill().fillna(0)
    return (last_signal > 0).astype(bool)


def _position_to_signals(position: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Derive entry/exit signal bars from a continuous position state series."""
    prev = position.shift(1).fillna(False)
    entries = (position & ~prev).astype(bool)
    exits = (~position & prev).astype(bool)
    return entries, exits


# ---------------------------------------------------------------------------
# Mode-specific position combiners
# ---------------------------------------------------------------------------

def _combine_positions_and(positions: list[pd.Series]) -> pd.Series:
    """In position only when ALL strategies are long."""
    result = positions[0]
    for p in positions[1:]:
        result = result & p
    return result


def _combine_positions_majority(positions: list[pd.Series]) -> pd.Series:
    """In position when more than half of strategies are long."""
    n = len(positions)
    votes = sum(p.astype(int) for p in positions)
    return (votes > (n / 2)).astype(bool)


def _combine_positions_weighted(
    positions: list[pd.Series],
    weights: list[float],
    threshold: float,
) -> pd.Series:
    """In position when the weighted fraction of long strategies exceeds threshold."""
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("Sum of weights must be > 0")
    score = sum(p.astype(float) * w for p, w in zip(positions, weights))
    return ((score / total_weight) > threshold).astype(bool)


# ---------------------------------------------------------------------------
# Public combination API
# ---------------------------------------------------------------------------

def combine_signals(
    signal_list: list[tuple[pd.Series, pd.Series]],
    mode: str,
    weights: list[float],
    threshold: float = 0.5,
) -> tuple[pd.Series, pd.Series]:
    """Combine multiple entry/exit signal pairs into a single pair.

    Each strategy's raw signals are first converted to a continuous position
    state, the states are combined, and the result is converted back to
    entry/exit bars.

    Modes:
    - "and": combined long when ALL strategies are simultaneously long.
    - "majority": combined long when >50% of strategies are long.
    - "weighted": combined long when weighted fraction exceeds threshold.
    """
    if not signal_list:
        raise ValueError("signal_list must not be empty")

    positions = [_signals_to_position(e, x) for e, x in signal_list]

    if mode == "and":
        combined = _combine_positions_and(positions)
    elif mode == "majority":
        combined = _combine_positions_majority(positions)
    elif mode == "weighted":
        combined = _combine_positions_weighted(positions, weights, threshold)
    else:
        raise ValueError(f"Unknown combination mode: {mode!r}. Valid: and, majority, weighted")

    return _position_to_signals(combined)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _build_combo_signals(
    df: pd.DataFrame,
    strategies: list[ComboStrategyConfig],
    mode: str,
    threshold: float,
) -> tuple[pd.Series, pd.Series]:
    signal_list: list[tuple[pd.Series, pd.Series]] = []
    for cfg in strategies:
        entries, exits = build_signal_array(df, cfg.strategy_name, cfg.strategy_params)
        signal_list.append((entries, exits))

    weights = [cfg.weight for cfg in strategies]
    return combine_signals(signal_list, mode, weights, threshold)


def run_combo_backtest(
    df: pd.DataFrame,
    strategies: list[ComboStrategyConfig],
    combination_mode: str,
    threshold: float = 0.5,
    initial_capital: float = 100_000.0,
    timeframe: str = "1d",
) -> BacktestResult:
    """Execute a combination backtest using vectorbt.

    Builds a position-state signal per strategy, combines them according to
    combination_mode, then runs a single vectorbt portfolio.
    """
    import vectorbt as vbt

    t0 = time.perf_counter()

    close = df.set_index("time")["close"] if "time" in df.columns else df["close"]
    close = close.astype(float)

    entries, exits = _build_combo_signals(df, strategies, combination_mode, threshold)

    vbt_freq = _TIMEFRAME_TO_VBT_FREQ.get(timeframe, "D")
    portfolio = vbt.Portfolio.from_signals(
        close,
        entries=entries,
        exits=exits,
        init_cash=initial_capital,
        fees=0.001,
        slippage=0.001,
        freq=vbt_freq,
    )

    equity = portfolio.value()
    returns = portfolio.returns()
    trades_df = _extract_trades(portfolio)
    metrics = compile_all_metrics(returns, equity, trades_df)

    equity_curve = [
        {"time": str(t), "value": float(v)}
        for t, v in equity.items()
    ]
    buy_hold_curve = _compute_buy_hold_curve(close, initial_capital)

    duration_ms = (time.perf_counter() - t0) * 1000
    strategy_names = "+".join(c.strategy_name for c in strategies)
    logger.info(
        "combo_backtest_complete",
        strategies=strategy_names,
        mode=combination_mode,
        timeframe=timeframe,
        sharpe=round(metrics.get("sharpe_ratio", 0), 3),
        num_trades=metrics.get("num_trades", 0),
        duration_ms=round(duration_ms, 2),
    )

    return BacktestResult(
        metrics=metrics,
        equity_curve=equity_curve,
        trade_log=trades_df,
        buy_hold_curve=buy_hold_curve,
        indicator_series=[],
        duration_ms=duration_ms,
    )
