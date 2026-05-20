"""Walk-forward optimization for Monte Carlo simulation config params."""
from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd

from dtos.simulation_dto import CalibratedModelParams
from features.backtesting.metrics import _safe_float
from features.backtesting.optimizer import (
    NO_FEASIBLE_MSG,
    generate_param_combinations,
    split_timeseries,
)
from features.quantitative_engine.calibration_service import calibrate_from_prices
from features.quantitative_engine.monte_carlo import SimulationResult
from features.quantitative_engine.regime_weight import calc_adx
from features.quantitative_engine.simulation_runner import dispatch_mc_simulation
from utils.logging import get_logger

logger = get_logger(__name__)

MAX_COMBOS = 50
ALLOWED_GRID_KEYS = frozenset({"num_paths", "calibration_years"})
VALID_METRICS = frozenset({
    "prob_positive_return",
    "p50",
    "mean_terminal",
    "p5",
    "mean_max_drawdown",
    "std_terminal",
})


@dataclass
class McSimulationOptimizationResult:
    best_params: dict
    best_metric: float
    best_avg_oos_max_drawdown: float | None
    all_results: list[dict]
    n_splits: int


def validate_param_grid(param_grid: dict) -> list[dict]:
    if not param_grid:
        raise ValueError("param_grid must not be empty")
    unknown = set(param_grid.keys()) - ALLOWED_GRID_KEYS
    if unknown:
        raise ValueError(f"Unsupported param_grid keys: {sorted(unknown)}")
    combos = generate_param_combinations(param_grid)
    if len(combos) > MAX_COMBOS:
        raise ValueError(f"Too many combinations ({len(combos)}); max is {MAX_COMBOS}")
    for combo in combos:
        num_paths = combo.get("num_paths", 1000)
        cal_years = combo.get("calibration_years", 10)
        if not (100 <= num_paths <= 50000):
            raise ValueError(f"num_paths must be between 100 and 50000, got {num_paths}")
        if not (1 <= cal_years <= 20):
            raise ValueError(f"calibration_years must be between 1 and 20, got {cal_years}")
    return combos


def _slice_calibration_prices(
    df: pd.DataFrame,
    end_idx: int,
    calibration_years: int,
) -> tuple[np.ndarray, pd.Timestamp, pd.Timestamp]:
    end_time = pd.to_datetime(df.iloc[end_idx]["time"])
    start_time = end_time - timedelta(days=calibration_years * 365)
    times = pd.to_datetime(df["time"])
    mask = (times >= start_time) & (times <= end_time)
    segment = df.loc[mask]
    if len(segment) < 30:
        raise ValueError(f"Insufficient calibration data: {len(segment)} rows")
    prices = segment["close"].to_numpy(dtype=float)
    return prices, pd.to_datetime(segment.iloc[0]["time"]), end_time


def calibrate_at_date(
    df: pd.DataFrame,
    end_idx: int,
    calibration_years: int,
    timeframe: str,
    ou_ma_window: int = 20,
) -> CalibratedModelParams:
    prices, cal_start, cal_end = _slice_calibration_prices(df, end_idx, calibration_years)
    return calibrate_from_prices(
        prices,
        timeframe,
        cal_start.to_pydatetime(),
        cal_end.to_pydatetime(),
        ou_ma_window=ou_ma_window,
    )


def _adx_at_index(df: pd.DataFrame, end_idx: int, period: int = 14) -> float:
    segment = df.iloc[: end_idx + 1]
    adx = calc_adx(
        segment["high"].astype(float),
        segment["low"].astype(float),
        segment["close"].astype(float),
        period=period,
    )
    val = float(adx.iloc[-1])
    return val if val == val else 20.0


def _is_sim_metric(stats, metric: str) -> float:
    if metric not in VALID_METRICS:
        raise ValueError(f"Unsupported optimize_metric: {metric}")
    return float(getattr(stats, metric, -np.inf))


def _actual_max_drawdown(closes: np.ndarray) -> float:
    cummax = np.maximum.accumulate(closes)
    dd = (closes - cummax) / np.where(cummax > 0, cummax, 1.0)
    return float(np.min(dd))


def _oos_predictive_score(
    actual_closes: np.ndarray,
    sim_result: SimulationResult,
    s0: float,
    metric: str,
) -> float:
    actual_terminal = float(actual_closes[-1])
    actual_return = (actual_terminal - s0) / s0 if s0 > 0 else 0.0
    stats = sim_result.stats

    if metric == "prob_positive_return":
        return 1.0 if actual_return > 0 else 0.0
    if metric in ("p50", "mean_terminal"):
        sim_ref = stats.p50 if metric == "p50" else stats.mean_terminal
        sim_return = (sim_ref - s0) / s0 if s0 > 0 else 0.0
        return -abs(actual_return - sim_return)
    if metric == "p5":
        sim_return = (stats.p5 - s0) / s0 if s0 > 0 else 0.0
        return -max(0.0, sim_return - actual_return)
    if metric == "mean_max_drawdown":
        actual_dd = _actual_max_drawdown(actual_closes)
        return -abs(actual_dd - stats.mean_max_drawdown)
    if metric == "std_terminal":
        sim_return = (stats.mean_terminal - s0) / s0 if s0 > 0 else 0.0
        return -abs(actual_return - sim_return)
    raise ValueError(f"Unsupported optimize_metric: {metric}")


def _run_combo_sim(
    df: pd.DataFrame,
    train_end_idx: int,
    test_len: int,
    params: dict,
    model_type: str,
    timeframe: str,
    horizon_steps: int,
    cal_cache: dict[int, CalibratedModelParams],
) -> SimulationResult:
    cal_years = int(params["calibration_years"])
    num_paths = int(params["num_paths"])
    if cal_years not in cal_cache:
        cal_cache[cal_years] = calibrate_at_date(df, train_end_idx, cal_years, timeframe)
    calibrated = cal_cache[cal_years]
    steps = min(horizon_steps, test_len)
    adx_val = _adx_at_index(df, train_end_idx) if model_type == "blended" else None
    return dispatch_mc_simulation(
        calibrated, model_type, num_paths, steps, timeframe, adx=adx_val,
    )


def _pick_best_train_combo(
    df: pd.DataFrame,
    train_end_idx: int,
    test_len: int,
    param_combos: list[dict],
    model_type: str,
    timeframe: str,
    horizon_steps: int,
    optimize_metric: str,
    fold_idx: int,
) -> int:
    best_metric = -np.inf
    best_idx = 0
    cal_cache: dict[int, CalibratedModelParams] = {}
    for combo_idx, params in enumerate(param_combos):
        try:
            result = _run_combo_sim(
                df, train_end_idx, test_len, params, model_type, timeframe, horizon_steps, cal_cache,
            )
            metric = _is_sim_metric(result.stats, optimize_metric)
            if metric > best_metric:
                best_metric = metric
                best_idx = combo_idx
        except Exception as exc:
            logger.warning("mc_wfo_is_failed", fold=fold_idx, combo=params, error=str(exc))
    return best_idx


def _record_oos_fold(
    df: pd.DataFrame,
    train_end_idx: int,
    test_df: pd.DataFrame,
    params: dict,
    model_type: str,
    timeframe: str,
    horizon_steps: int,
    optimize_metric: str,
    combo_idx: int,
    combo_scores: dict[int, list[float]],
    combo_oos_drawdowns: dict[int, list[float]],
    fold_idx: int,
) -> None:
    test_closes = test_df["close"].to_numpy(dtype=float)
    s0 = float(df.iloc[train_end_idx]["close"])
    cal_cache: dict[int, CalibratedModelParams] = {}
    try:
        result = _run_combo_sim(
            df, train_end_idx, len(test_df), params, model_type, timeframe, horizon_steps, cal_cache,
        )
        oos_score = _oos_predictive_score(test_closes, result, s0, optimize_metric)
        oos_dd = _actual_max_drawdown(test_closes)
        combo_scores[combo_idx].append(oos_score)
        combo_oos_drawdowns[combo_idx].append(oos_dd)
        logger.info(
            "mc_wfo_fold_done",
            fold=fold_idx,
            params=params,
            oos_metric=round(oos_score, 4),
            oos_max_drawdown=round(oos_dd, 4),
        )
    except Exception as exc:
        logger.warning("mc_wfo_oos_failed", fold=fold_idx, error=str(exc))


def _aggregate_combo_stats(
    combo_scores: dict[int, list[float]],
    combo_oos_drawdowns: dict[int, list[float]],
) -> tuple[dict[int, float], dict[int, float | None]]:
    avg_scores = {
        idx: (_safe_float(np.mean(scores)) if scores else 0.0)
        for idx, scores in combo_scores.items()
    }
    avg_drawdowns = {
        idx: (_safe_float(np.mean(dds)) if dds else None)
        for idx, dds in combo_oos_drawdowns.items()
    }
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
        idx for idx in avg_scores
        if _is_feasible(idx, combo_scores, avg_drawdowns[idx], max_drawdown_cap)
    ]
    if not feasible:
        raise ValueError(NO_FEASIBLE_MSG)
    return max(feasible, key=lambda i: avg_scores[i])


def walk_forward_mc_simulation_optimize(
    df: pd.DataFrame,
    param_grid: dict,
    n_splits: int,
    model_type: str,
    timeframe: str,
    horizon_steps: int,
    optimize_metric: str,
    max_drawdown_cap: float | None = None,
) -> McSimulationOptimizationResult:
    """Walk-forward MC simulation optimization over config param grid."""
    if optimize_metric not in VALID_METRICS:
        raise ValueError(f"Unsupported optimize_metric: {optimize_metric}")

    param_combos = validate_param_grid(param_grid)
    splits = split_timeseries(df.reset_index(drop=True), n_splits)
    if not splits:
        raise ValueError("Insufficient data for walk-forward optimization")

    n_combos = len(param_combos)
    combo_scores: dict[int, list[float]] = {i: [] for i in range(n_combos)}
    combo_oos_drawdowns: dict[int, list[float]] = {i: [] for i in range(n_combos)}
    work_df = df.reset_index(drop=True)

    logger.info(
        "mc_wfo_start",
        n_combos=n_combos,
        n_splits=len(splits),
        optimize_metric=optimize_metric,
    )

    for fold_idx, (train_df, test_df) in enumerate(splits):
        train_end_idx = len(train_df) - 1
        best_idx = _pick_best_train_combo(
            work_df,
            train_end_idx,
            len(test_df),
            param_combos,
            model_type,
            timeframe,
            horizon_steps,
            optimize_metric,
            fold_idx,
        )
        _record_oos_fold(
            work_df,
            train_end_idx,
            test_df,
            param_combos[best_idx],
            model_type,
            timeframe,
            horizon_steps,
            optimize_metric,
            best_idx,
            combo_scores,
            combo_oos_drawdowns,
            fold_idx,
        )

    avg_scores, avg_drawdowns = _aggregate_combo_stats(combo_scores, combo_oos_drawdowns)
    best_idx = _select_best_combo(avg_scores, avg_drawdowns, combo_scores, max_drawdown_cap)
    all_results = [
        {
            "params": param_combos[i],
            "avg_oos_metric": avg_scores[i],
            "avg_oos_max_drawdown": avg_drawdowns[i],
        }
        for i in range(n_combos)
    ]
    return McSimulationOptimizationResult(
        best_params=param_combos[best_idx],
        best_metric=_safe_float(avg_scores[best_idx]),
        best_avg_oos_max_drawdown=avg_drawdowns[best_idx],
        all_results=all_results,
        n_splits=n_splits,
    )


def run_best_params_simulation(
    df: pd.DataFrame,
    best_params: dict,
    model_type: str,
    timeframe: str,
    horizon_steps: int,
) -> SimulationResult:
    """Run full forward simulation at end of dataframe with best params."""
    end_idx = len(df) - 1
    cal_years = int(best_params["calibration_years"])
    num_paths = int(best_params["num_paths"])
    calibrated = calibrate_at_date(df, end_idx, cal_years, timeframe)
    adx_val = _adx_at_index(df, end_idx) if model_type == "blended" else None
    return dispatch_mc_simulation(
        calibrated, model_type, num_paths, horizon_steps, timeframe, adx=adx_val,
    )
