"""vectorbt-backed backtesting runner."""
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from features.backtesting.metrics import compile_all_metrics
from features.backtesting.strategies import build_signal_array
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BacktestResult:
    metrics: dict
    equity_curve: list[dict]
    trade_log: list[dict]
    duration_ms: float


def run_backtest(
    df: pd.DataFrame,
    strategy: str,
    params: dict,
    initial_capital: float = 100_000.0,
) -> BacktestResult:
    """Execute a single backtest using vectorbt.

    df must have columns: time, open, high, low, close, volume (DatetimeIndex).
    """
    import vectorbt as vbt

    t0 = time.perf_counter()

    close = df.set_index("time")["close"] if "time" in df.columns else df["close"]
    close = close.astype(float)

    entries, exits = build_signal_array(df, strategy, params)

    portfolio = vbt.Portfolio.from_signals(
        close,
        entries=entries,
        exits=exits,
        init_cash=initial_capital,
        fees=0.001,
        slippage=0.001,
        freq="D",
    )

    equity = portfolio.value()
    returns = portfolio.returns()
    trades_df = _extract_trades(portfolio)

    metrics = compile_all_metrics(returns, equity, trades_df)

    equity_curve = [
        {"time": str(t), "value": float(v)}
        for t, v in equity.items()
    ]

    duration_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "backtest_complete",
        strategy=strategy,
        sharpe=round(metrics.get("sharpe_ratio", 0), 3),
        num_trades=metrics.get("num_trades", 0),
        duration_ms=round(duration_ms, 2),
    )

    return BacktestResult(
        metrics=metrics,
        equity_curve=equity_curve,
        trade_log=trades_df,
        duration_ms=duration_ms,
    )


def prepare_simulated_dataframe(simulation_record: Any) -> pd.DataFrame:
    """Convert a stored Monte Carlo simulation record into a backtest-compatible DataFrame.

    Uses the p50 (median) percentile path as the representative price series.
    Raises ValueError if the record has no percentile paths.
    """
    percentile_paths = simulation_record.percentile_paths
    if not percentile_paths:
        raise ValueError("Simulation record has no percentile_paths data")

    path_key = "p50" if "p50" in percentile_paths else next(iter(percentile_paths))
    prices = percentile_paths[path_key]

    s0 = float(simulation_record.s0)
    close_series = pd.Series([s0 * p for p in prices], dtype=float)

    start_date = simulation_record.created_at
    dates = pd.date_range(start=start_date, periods=len(close_series), freq="D")

    df = pd.DataFrame({
        "time": dates,
        "open": close_series,
        "high": close_series,
        "low": close_series,
        "close": close_series,
        "volume": 0.0,
    })
    logger.info(
        "simulated_df_prepared",
        path_key=path_key,
        rows=len(df),
        s0=s0,
    )
    return df


def _extract_trades(portfolio) -> list[dict]:
    """Convert vectorbt trade records to serializable list."""
    try:
        trades = portfolio.trades.records_readable
        result = []
        for _, row in trades.iterrows():
            result.append({
                "entry_time": str(row.get("Entry Timestamp", "")),
                "exit_time": str(row.get("Exit Timestamp", "")),
                "direction": str(row.get("Direction", "long")),
                "entry_price": float(row.get("Avg Entry Price", 0)),
                "exit_price": float(row.get("Avg Exit Price", 0)),
                "pnl": float(row.get("PnL", 0)),
                "return_pct": float(row.get("Return", 0)),
            })
        return result
    except Exception as exc:
        logger.warning("trade_extraction_failed", error=str(exc))
        return []
