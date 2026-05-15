"""vectorbt-backed backtesting runner."""
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from features.backtesting.indicator_functions import INDICATOR_MAP, _empty_indicators
from features.backtesting.metrics import compile_all_metrics
from features.backtesting.strategies import build_signal_array
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BacktestResult:
    metrics: dict
    equity_curve: list[dict]
    trade_log: list[dict]
    buy_hold_curve: list[dict]
    indicator_series: list[dict]
    duration_ms: float


_TIMEFRAME_TO_VBT_FREQ: dict[str, str] = {
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "h",
    "4h": "4h",
    "1d": "D",
    "1w": "W",
}


def run_backtest(
    df: pd.DataFrame,
    strategy: str,
    params: dict,
    initial_capital: float = 100_000.0,
    timeframe: str = "1d",
) -> BacktestResult:
    """Execute a single backtest using vectorbt.

    df must have columns: time, open, high, low, close, volume (DatetimeIndex).
    timeframe controls the vectorbt portfolio frequency used for metric annualisation.
    """
    import vectorbt as vbt

    t0 = time.perf_counter()

    close = df.set_index("time")["close"] if "time" in df.columns else df["close"]
    close = close.astype(float)

    entries, exits = build_signal_array(df, strategy, params)

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
    indicator_series = _compute_indicator_series(df, strategy, params)

    duration_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "backtest_complete",
        strategy=strategy,
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
        indicator_series=indicator_series,
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


def _safe_float(v) -> float | None:
    """Return None for NaN / inf / non-numeric values."""
    try:
        f = float(v)
        return None if not np.isfinite(f) else round(f, 6)
    except (TypeError, ValueError):
        return None


def _compute_indicator_series(
    df: pd.DataFrame,
    strategy: str,
    params: dict,
) -> list[dict]:
    """Compute per-bar indicator values for a strategy and return them as a list of dicts.

    Each dict has a 'time' key plus one key per indicator column.
    NaN / inf values are set to None for safe JSON serialisation.
    Returns an empty list for strategies with no meaningful indicators.
    """
    indicator_fn = INDICATOR_MAP.get(strategy, _empty_indicators)
    ind_df = indicator_fn(df, params)

    if ind_df.empty or ind_df.shape[1] == 0:
        return []

    if "time" in df.columns:
        times = df["time"].astype(str).tolist()
    else:
        times = [str(t) for t in df.index]

    rows: list[dict] = []
    for i, row in enumerate(ind_df.itertuples(index=False)):
        entry: dict = {"time": times[i] if i < len(times) else str(i)}
        for col in ind_df.columns:
            entry[col] = _safe_float(getattr(row, col))
        rows.append(entry)
    return rows


def _compute_buy_hold_curve(close: pd.Series, initial_capital: float) -> list[dict]:
    """Return a buy-and-hold equity curve normalised to initial_capital."""
    first = float(close.iloc[0])
    if first == 0:
        return []
    return [
        {"time": str(t), "value": round((float(v) / first) * initial_capital, 4)}
        for t, v in close.items()
    ]


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
