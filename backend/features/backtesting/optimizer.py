"""Walk-forward optimization to avoid overfitting."""
import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd

from features.backtesting.metrics import _safe_float
from features.backtesting.runner import BacktestResult, run_backtest
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OptimizationResult:
    best_params: dict
    best_sharpe: float
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


def walk_forward_optimize(
    df: pd.DataFrame,
    strategy: str,
    param_grid: dict,
    n_splits: int = 5,
    initial_capital: float = 100_000.0,
    optimize_metric: str = "sharpe_ratio",
) -> OptimizationResult:
    """Walk-forward optimization: train on in-sample, validate on out-of-sample.

    Returns best parameter set by average out-of-sample Sharpe.
    """
    param_combos = generate_param_combinations(param_grid)
    splits = split_timeseries(df, n_splits)

    if not splits:
        raise ValueError("Insufficient data for walk-forward optimization")

    logger.info(
        "wfo_start",
        strategy=strategy,
        n_combos=len(param_combos),
        n_splits=len(splits),
    )

    combo_scores: dict[int, list[float]] = {i: [] for i in range(len(param_combos))}

    for fold_idx, (train_df, test_df) in enumerate(splits):
        best_train_metric = -np.inf
        best_combo_idx = 0

        for combo_idx, params in enumerate(param_combos):
            try:
                result = run_backtest(train_df, strategy, params, initial_capital)
                metric = result.metrics.get(optimize_metric, -np.inf)
                if metric > best_train_metric:
                    best_train_metric = metric
                    best_combo_idx = combo_idx
            except Exception as exc:
                logger.warning("wfo_combo_failed", fold=fold_idx, combo=params, error=str(exc))

        best_params = param_combos[best_combo_idx]
        try:
            test_result = run_backtest(test_df, strategy, best_params, initial_capital)
            oos_metric = test_result.metrics.get(optimize_metric, -np.inf)
            combo_scores[best_combo_idx].append(oos_metric)
            logger.info("wfo_fold_done", fold=fold_idx, params=best_params, oos_metric=round(oos_metric, 4))
        except Exception as exc:
            logger.warning("wfo_test_fold_failed", fold=fold_idx, error=str(exc))

    avg_scores = {
        idx: (_safe_float(np.mean(scores)) if scores else 0.0)
        for idx, scores in combo_scores.items()
    }
    best_idx = max(avg_scores, key=avg_scores.get)
    best_params = param_combos[best_idx]
    best_sharpe = avg_scores[best_idx]

    all_results = [
        {"params": param_combos[i], "avg_oos_metric": avg_scores[i]}
        for i in range(len(param_combos))
    ]

    logger.info("wfo_complete", best_params=best_params, best_oos_metric=round(best_sharpe, 4))
    return OptimizationResult(
        best_params=best_params,
        best_sharpe=_safe_float(best_sharpe),
        all_results=all_results,
        n_splits=n_splits,
    )
