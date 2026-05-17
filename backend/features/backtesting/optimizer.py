"""Walk-forward optimization to avoid overfitting."""
import itertools
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from features.backtesting.metrics import _safe_float
from features.backtesting.runner import run_backtest
from features.backtesting.warmup import (
    evaluation_mask,
    max_warmup_bars_from_grid,
    slice_df_segment,
)
from utils.logging import get_logger

logger = get_logger(__name__)

NO_FEASIBLE_MSG = (
    "No parameter combination satisfies the max drawdown cap with at least one "
    "successful out-of-sample fold"
)


@dataclass
class OptimizationResult:
    best_params: dict
    best_sharpe: float
    best_avg_oos_max_drawdown: float | None
    all_results: list[dict]
    n_splits: int


def generate_param_combinations(param_grid: dict) -> list[dict]:
    """Cartesian product of all parameter values."""
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combos = []
    for combo in itertools.product(*values):
        combos.append(dict(zip(keys, combo)))
    return combos


def split_timeseries(df: pd.DataFrame, n_splits: int) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """Split a time-sorted DataFrame into n train/test folds (walk-forward)."""
    n = len(df)
    split_size = n // (n_splits + 1)
    splits = []
    for i in range(1, n_splits + 1):
        train_end = i * split_size
        test_end = min((i + 1) * split_size, n)
        train = df.iloc[:train_end]
        test = df.iloc[train_end:test_end]
        if not train.empty and not test.empty:
            splits.append((train, test))
    return splits


def _pick_best_train_combo(
    train_chunk: pd.DataFrame,
    strategy: str,
    param_combos: list[dict],
    optimize_metric: str,
    initial_capital: float,
    train_eval: datetime,
    fold_idx: int,
) -> int:
    best_train_metric = -np.inf
    best_combo_idx = 0
    for combo_idx, params in enumerate(param_combos):
        try:
            result = run_backtest(
                train_chunk,
                strategy,
                params,
                initial_capital,
                evaluation_start=train_eval,
            )
            metric = result.metrics.get(optimize_metric, -np.inf)
            if metric > best_train_metric:
                best_train_metric = metric
                best_combo_idx = combo_idx
        except Exception as exc:
            logger.warning("wfo_combo_failed", fold=fold_idx, combo=params, error=str(exc))
    return best_combo_idx


def _record_oos_fold(
    df: pd.DataFrame,
    test_df: pd.DataFrame,
    strategy: str,
    best_params: dict,
    warmup_bars: int,
    initial_capital: float,
    optimize_metric: str,
    combo_idx: int,
    combo_scores: dict[int, list[float]],
    combo_oos_drawdowns: dict[int, list[float]],
    fold_idx: int,
) -> None:
    test_start = pd.to_datetime(test_df.iloc[0]["time"]).to_pydatetime()
    test_end = pd.to_datetime(test_df.iloc[-1]["time"]).to_pydatetime()
    test_chunk, test_eval = slice_df_segment(df, test_start, test_end, warmup_bars)
    try:
        test_result = run_backtest(
            test_chunk,
            strategy,
            best_params,
            initial_capital,
            evaluation_start=test_eval,
        )
        oos_metric = test_result.metrics.get(optimize_metric, -np.inf)
        oos_drawdown = test_result.metrics.get("max_drawdown", 0.0)
        combo_scores[combo_idx].append(oos_metric)
        combo_oos_drawdowns[combo_idx].append(oos_drawdown)
        logger.info(
            "wfo_fold_done",
            fold=fold_idx,
            params=best_params,
            oos_metric=round(oos_metric, 4),
            oos_max_drawdown=round(oos_drawdown, 4),
        )
    except Exception as exc:
        logger.warning("wfo_test_fold_failed", fold=fold_idx, error=str(exc))


def _mean_or_none(values: list[float]) -> float | None:
    return _safe_float(np.mean(values)) if values else None


def _aggregate_combo_stats(
    combo_scores: dict[int, list[float]],
    combo_oos_drawdowns: dict[int, list[float]],
) -> tuple[dict[int, float], dict[int, float | None]]:
    avg_scores = {
        idx: (_safe_float(np.mean(scores)) if scores else 0.0)
        for idx, scores in combo_scores.items()
    }
    avg_drawdowns = {idx: _mean_or_none(dds) for idx, dds in combo_oos_drawdowns.items()}
    return avg_scores, avg_drawdowns


def _is_feasible(
    combo_idx: int,
    combo_scores: dict[int, list[float]],
    avg_drawdown: float | None,
    max_drawdown_cap: float | None,
) -> bool:
    if not combo_scores[combo_idx]:
        return False
    if max_drawdown_cap is None:
        return True
    if avg_drawdown is None:
        return False
    return avg_drawdown >= max_drawdown_cap


def _select_best_combo(
    avg_scores: dict[int, float],
    avg_drawdowns: dict[int, float | None],
    combo_scores: dict[int, list[float]],
    max_drawdown_cap: float | None,
) -> int:
    feasible = [
        idx
        for idx in avg_scores
        if _is_feasible(idx, combo_scores, avg_drawdowns[idx], max_drawdown_cap)
    ]
    if not feasible:
        raise ValueError(NO_FEASIBLE_MSG)
    return max(feasible, key=lambda i: avg_scores[i])


def walk_forward_optimize(
    df: pd.DataFrame,
    strategy: str,
    param_grid: dict,
    n_splits: int = 5,
    initial_capital: float = 100_000.0,
    optimize_metric: str = "sharpe_ratio",
    evaluation_start: datetime | None = None,
    max_drawdown_cap: float | None = None,
) -> OptimizationResult:
    """Walk-forward optimization: train on in-sample, validate on out-of-sample."""
    param_combos = generate_param_combinations(param_grid)
    warmup_bars = max_warmup_bars_from_grid(strategy, param_grid)
    work_df = df
    if evaluation_start is not None:
        work_df = df.loc[evaluation_mask(df, evaluation_start)].reset_index(drop=True)
    splits = split_timeseries(work_df, n_splits)

    if not splits:
        raise ValueError("Insufficient data for walk-forward optimization")

    logger.info(
        "wfo_start",
        strategy=strategy,
        n_combos=len(param_combos),
        n_splits=len(splits),
        max_drawdown_cap=max_drawdown_cap,
    )

    n_combos = len(param_combos)
    combo_scores: dict[int, list[float]] = {i: [] for i in range(n_combos)}
    combo_oos_drawdowns: dict[int, list[float]] = {i: [] for i in range(n_combos)}

    for fold_idx, (train_df, test_df) in enumerate(splits):
        train_start = pd.to_datetime(train_df.iloc[0]["time"]).to_pydatetime()
        train_end = pd.to_datetime(train_df.iloc[-1]["time"]).to_pydatetime()
        train_chunk, train_eval = slice_df_segment(df, train_start, train_end, warmup_bars)

        best_combo_idx = _pick_best_train_combo(
            train_chunk,
            strategy,
            param_combos,
            optimize_metric,
            initial_capital,
            train_eval,
            fold_idx,
        )
        _record_oos_fold(
            df,
            test_df,
            strategy,
            param_combos[best_combo_idx],
            warmup_bars,
            initial_capital,
            optimize_metric,
            best_combo_idx,
            combo_scores,
            combo_oos_drawdowns,
            fold_idx,
        )

    avg_scores, avg_drawdowns = _aggregate_combo_stats(combo_scores, combo_oos_drawdowns)
    best_idx = _select_best_combo(avg_scores, avg_drawdowns, combo_scores, max_drawdown_cap)
    best_params = param_combos[best_idx]
    best_metric = avg_scores[best_idx]
    best_dd = avg_drawdowns[best_idx]

    all_results = [
        {
            "params": param_combos[i],
            "avg_oos_metric": avg_scores[i],
            "avg_oos_max_drawdown": avg_drawdowns[i],
        }
        for i in range(n_combos)
    ]

    logger.info(
        "wfo_complete",
        best_params=best_params,
        best_oos_metric=round(best_metric, 4),
        best_avg_oos_max_drawdown=round(best_dd, 4) if best_dd is not None else None,
    )
    return OptimizationResult(
        best_params=best_params,
        best_sharpe=_safe_float(best_metric),
        best_avg_oos_max_drawdown=best_dd,
        all_results=all_results,
        n_splits=n_splits,
    )
