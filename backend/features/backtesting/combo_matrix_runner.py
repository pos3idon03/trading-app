"""Pairwise strategy combination matrix for heatmap visualisation."""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

from features.backtesting.combo_runner import (
    ComboStrategyConfig,
    combine_signals,
    run_backtest,
    run_portfolio_from_signals,
)
from features.backtesting.stance import compute_strategy_stance
from utils.logging import get_logger

logger = get_logger(__name__)

COMBO_MATRIX_MAX_WORKERS = 4

VALID_MATRIX_METRICS = frozenset({
    "sharpe_ratio",
    "sortino_ratio",
    "total_return",
    "profit_factor",
})


@dataclass
class ComboMatrixResult:
    strategies: list[str]
    metric: str
    combination_mode: str
    values: list[list[Optional[float]]]
    duration_ms: float


def precompute_stances(
    df: pd.DataFrame,
    configs: list[ComboStrategyConfig],
) -> dict[str, pd.Series]:
    """Compute per-strategy stance series once for matrix reuse."""
    return {
        cfg.strategy_name: compute_strategy_stance(
            df, cfg.strategy_name, cfg.strategy_params
        )
        for cfg in configs
    }


def _extract_metric(metrics: dict, metric_key: str) -> Optional[float]:
    value = metrics.get(metric_key)
    if value is None:
        return None
    try:
        f = float(value)
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return round(f, 6)
    except (TypeError, ValueError):
        return None


def _metric_from_stances(
    df: pd.DataFrame,
    stance_a: pd.Series,
    stance_b: pd.Series,
    *,
    combination_mode: str,
    threshold: float,
    initial_capital: float,
    timeframe: str,
    evaluation_start: datetime | None,
    metric_key: str,
) -> Optional[float]:
    entries, exits = combine_signals(
        [stance_a, stance_b],
        combination_mode,
        [1.0, 1.0],
        threshold,
    )
    run_result = run_portfolio_from_signals(
        df,
        entries,
        exits,
        initial_capital=initial_capital,
        timeframe=timeframe,
        evaluation_start=evaluation_start,
    )
    return _extract_metric(run_result.metrics, metric_key)


def _metric_from_single(
    df: pd.DataFrame,
    strategy_name: str,
    params: dict,
    *,
    initial_capital: float,
    timeframe: str,
    evaluation_start: datetime | None,
    metric_key: str,
) -> Optional[float]:
    result = run_backtest(
        df,
        strategy=strategy_name,
        params=params,
        initial_capital=initial_capital,
        timeframe=timeframe,
        evaluation_start=evaluation_start,
    )
    return _extract_metric(result.metrics, metric_key)


def _build_config_map(
    strategies: list[str],
    strategy_params: dict[str, dict],
) -> dict[str, ComboStrategyConfig]:
    return {
        name: ComboStrategyConfig(
            strategy_name=name,
            strategy_params=strategy_params.get(name, {}),
            weight=1.0,
        )
        for name in strategies
    }


def _evaluate_cell(
    df: pd.DataFrame,
    row_name: str,
    col_name: str,
    stance_map: dict[str, pd.Series],
    config_map: dict[str, ComboStrategyConfig],
    *,
    combination_mode: str,
    threshold: float,
    initial_capital: float,
    timeframe: str,
    evaluation_start: datetime | None,
    metric_key: str,
) -> tuple[int, int, Optional[float]]:
    try:
        if row_name == col_name:
            cfg = config_map[row_name]
            value = _metric_from_single(
                df,
                row_name,
                cfg.strategy_params,
                initial_capital=initial_capital,
                timeframe=timeframe,
                evaluation_start=evaluation_start,
                metric_key=metric_key,
            )
        else:
            value = _metric_from_stances(
                df,
                stance_map[row_name],
                stance_map[col_name],
                combination_mode=combination_mode,
                threshold=threshold,
                initial_capital=initial_capital,
                timeframe=timeframe,
                evaluation_start=evaluation_start,
                metric_key=metric_key,
            )
        return row_name, col_name, value
    except Exception as exc:
        logger.warning(
            "combo_matrix_cell_failed",
            row=row_name,
            col=col_name,
            error=str(exc),
        )
        return row_name, col_name, None


def build_symmetric_matrix(
    df: pd.DataFrame,
    strategies: list[str],
    strategy_params: dict[str, dict],
    *,
    combination_mode: str,
    threshold: float = 0.5,
    metric: str,
    initial_capital: float = 100_000.0,
    timeframe: str = "1d",
    evaluation_start: datetime | None = None,
    max_workers: int = COMBO_MATRIX_MAX_WORKERS,
) -> list[list[Optional[float]]]:
    """Build N×N symmetric metric matrix (diagonal = solo strategy)."""
    if metric not in VALID_MATRIX_METRICS:
        raise ValueError(f"Unknown metric: {metric!r}")

    n = len(strategies)
    matrix: list[list[Optional[float]]] = [[None] * n for _ in range(n)]
    config_map = _build_config_map(strategies, strategy_params)
    configs = [config_map[s] for s in strategies]
    stance_map = precompute_stances(df, configs)

    tasks = [
        (i, j, strategies[i], strategies[j])
        for i in range(n)
        for j in range(i, n)
    ]

    def run_task(task: tuple[int, int, str, str]) -> tuple[int, int, Optional[float]]:
        i, j, row_name, col_name = task
        _, _, value = _evaluate_cell(
            df,
            row_name,
            col_name,
            stance_map,
            config_map,
            combination_mode=combination_mode,
            threshold=threshold,
            initial_capital=initial_capital,
            timeframe=timeframe,
            evaluation_start=evaluation_start,
            metric_key=metric,
        )
        return i, j, value

    workers = min(max_workers, max(1, len(tasks)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_task, t): t for t in tasks}
        for future in as_completed(futures):
            i, j, value = future.result()
            matrix[i][j] = value
            matrix[j][i] = value

    return matrix


def run_combo_matrix(
    df: pd.DataFrame,
    strategies: list[str],
    strategy_params: dict[str, dict],
    *,
    combination_mode: str,
    threshold: float = 0.5,
    metric: str,
    initial_capital: float = 100_000.0,
    timeframe: str = "1d",
    evaluation_start: datetime | None = None,
) -> ComboMatrixResult:
    """Run full strategy combination matrix and return heatmap values."""
    t0 = time.perf_counter()
    values = build_symmetric_matrix(
        df,
        strategies,
        strategy_params,
        combination_mode=combination_mode,
        threshold=threshold,
        metric=metric,
        initial_capital=initial_capital,
        timeframe=timeframe,
        evaluation_start=evaluation_start,
    )
    duration_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "combo_matrix_complete",
        n_strategies=len(strategies),
        metric=metric,
        mode=combination_mode,
        duration_ms=round(duration_ms, 2),
    )
    return ComboMatrixResult(
        strategies=strategies,
        metric=metric,
        combination_mode=combination_mode,
        values=values,
        duration_ms=duration_ms,
    )
