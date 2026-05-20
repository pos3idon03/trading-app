"""Multi-strategy combination backtest runner.

Combination uses per-bar **stance** (Buy / Neutral / Sell) per leg:
  - AND: all Buy → long; all Sell → flat; otherwise hold prior position.
  - Majority / weighted: Neutral abstains; ties or no votes → hold prior position.
"""
import time
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from features.backtesting.metrics import compile_all_metrics
from features.backtesting.runner import (
    BacktestResult,
    _TIMEFRAME_TO_VBT_FREQ,
    _compute_buy_hold_curve,
    _extract_trades,
    run_backtest,
)
from features.backtesting.stance import (
    build_signal_timeline_from_stance,
    combine_stances,
    compute_strategy_stance,
)
from features.backtesting.warmup import (
    evaluation_mask,
    slice_time_series_rows,
    slice_trade_log,
)
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ComboStrategyConfig:
    strategy_name: str
    strategy_params: dict
    weight: float = 1.0
    timeframe: str = "1d"


# ---------------------------------------------------------------------------
# Position-state helpers (entries/exits for vectorbt)
# ---------------------------------------------------------------------------

def _signals_to_position(entries: pd.Series, exits: pd.Series) -> pd.Series:
    """Convert entry/exit signal bars to a continuous boolean position state."""
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
# Public combination API
# ---------------------------------------------------------------------------

def combine_signals(
    stance_list: list[pd.Series],
    mode: str,
    weights: list[float],
    threshold: float = 0.5,
) -> tuple[pd.Series, pd.Series]:
    """Combine stance series into entry/exit bars for vectorbt.

    Args:
        stance_list: Per-strategy Buy/Neutral/Sell series aligned to the same index.
    """
    combined = combine_stances(stance_list, mode, weights, threshold)
    return _position_to_signals(combined)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _needs_multi_timeframe(
    strategies: list[ComboStrategyConfig],
    execution_timeframe: str,
) -> bool:
    exec_tf = execution_timeframe
    return any((cfg.timeframe or exec_tf) != exec_tf for cfg in strategies)


def _build_combo_signals(
    df: pd.DataFrame,
    strategies: list[ComboStrategyConfig],
    mode: str,
    threshold: float,
    execution_timeframe: str = "1d",
) -> tuple[pd.Series, pd.Series]:
    if _needs_multi_timeframe(strategies, execution_timeframe):
        from features.backtesting.multi_timeframe_combo import build_multi_tf_combo_signals

        return build_multi_tf_combo_signals(
            df, strategies, execution_timeframe, mode, threshold
        )

    stance_list = [
        compute_strategy_stance(df, cfg.strategy_name, cfg.strategy_params)
        for cfg in strategies
    ]
    weights = [cfg.weight for cfg in strategies]
    return combine_signals(stance_list, mode, weights, threshold)


@dataclass
class PortfolioRunResult:
    metrics: dict
    equity: pd.Series
    close: pd.Series
    trades_df: list[dict]


def run_portfolio_from_signals(
    df: pd.DataFrame,
    entries: pd.Series,
    exits: pd.Series,
    *,
    initial_capital: float = 100_000.0,
    timeframe: str = "1d",
    evaluation_start: datetime | None = None,
) -> PortfolioRunResult:
    """Run vectorbt portfolio from entry/exit bars."""
    import vectorbt as vbt

    if evaluation_start is not None:
        mask = evaluation_mask(df, evaluation_start)
        df_eval = df.loc[mask].reset_index(drop=True)
        entries = entries.loc[mask].reset_index(drop=True)
        exits = exits.loc[mask].reset_index(drop=True)
    else:
        df_eval = df

    close = df_eval.set_index("time")["close"] if "time" in df_eval.columns else df_eval["close"]
    close = close.astype(float)

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
    raw_trades = _extract_trades(portfolio)
    trades_df = (
        slice_trade_log(raw_trades, evaluation_start)
        if evaluation_start
        else raw_trades
    )
    metrics = compile_all_metrics(returns, equity, trades_df)
    return PortfolioRunResult(metrics=metrics, equity=equity, close=close, trades_df=trades_df)


def run_combo_backtest(
    df: pd.DataFrame,
    strategies: list[ComboStrategyConfig],
    combination_mode: str,
    threshold: float = 0.5,
    initial_capital: float = 100_000.0,
    timeframe: str = "1d",
    evaluation_start: datetime | None = None,
) -> BacktestResult:
    """Execute a combination backtest using vectorbt."""
    t0 = time.perf_counter()

    entries, exits = _build_combo_signals(
        df, strategies, combination_mode, threshold, timeframe,
    )
    exec_df = df
    if _needs_multi_timeframe(strategies, timeframe):
        from features.backtesting.multi_timeframe_combo import resample_ohlcv_df

        exec_df = resample_ohlcv_df(df, timeframe)

    run_result = run_portfolio_from_signals(
        exec_df,
        entries,
        exits,
        initial_capital=initial_capital,
        timeframe=timeframe,
        evaluation_start=evaluation_start,
    )
    metrics = run_result.metrics
    equity_curve = [
        {"time": str(t), "value": float(v)}
        for t, v in run_result.equity.items()
    ]
    buy_hold_curve = _compute_buy_hold_curve(run_result.close, initial_capital)

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
        trade_log=run_result.trades_df,
        buy_hold_curve=buy_hold_curve,
        indicator_series=[],
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# Per-strategy signal details for combo visualisation
# ---------------------------------------------------------------------------

@dataclass
class StrategySignalResult:
    strategy_name: str
    trade_log: list[dict]
    indicator_series: list[dict]
    equity_curve: list[dict]
    buy_hold_curve: list[dict]
    signal_timeline: list[dict]


def run_per_strategy_backtests(
    df: pd.DataFrame,
    strategies: list[ComboStrategyConfig],
    timeframe: str = "1d",
    initial_capital: float = 100_000.0,
    evaluation_start: datetime | None = None,
) -> list[StrategySignalResult]:
    """Run individual backtests for each combo leg and return per-strategy results."""
    results: list[StrategySignalResult] = []
    from features.backtesting.multi_timeframe_combo import resample_ohlcv_df

    for cfg in strategies:
        leg_tf = cfg.timeframe or timeframe
        leg_df = resample_ohlcv_df(df, leg_tf)

        result = run_backtest(
            leg_df,
            strategy=cfg.strategy_name,
            params=cfg.strategy_params,
            initial_capital=initial_capital,
            timeframe=leg_tf,
            evaluation_start=evaluation_start,
        )
        stance = compute_strategy_stance(leg_df, cfg.strategy_name, cfg.strategy_params)
        timeline = build_signal_timeline_from_stance(leg_df, stance)
        if evaluation_start is not None:
            timeline = slice_time_series_rows(timeline, evaluation_start)
        results.append(
            StrategySignalResult(
                strategy_name=cfg.strategy_name,
                trade_log=result.trade_log if isinstance(result.trade_log, list) else [],
                indicator_series=result.indicator_series or [],
                equity_curve=result.equity_curve,
                buy_hold_curve=result.buy_hold_curve,
                signal_timeline=timeline,
            )
        )
        logger.info(
            "per_strategy_backtest_complete",
            strategy=cfg.strategy_name,
            timeframe=timeframe,
        )
    return results
