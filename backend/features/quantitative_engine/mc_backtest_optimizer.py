"""Walk-forward optimization for MC backtest trading parameters."""
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from features.backtesting.metrics import _safe_float
from features.backtesting.optimizer import (
    NO_FEASIBLE_MSG,
    generate_param_combinations,
    split_timeseries,
)
from features.quantitative_engine.mc_backtest import McBacktestConfig, run_mc_backtest
from features.quantitative_engine.mc_intraday import (
    default_calibration_days,
    is_intraday_timeframe,
    resolve_calibration_lookback_days,
)
from utils.logging import get_logger

logger = get_logger(__name__)

MAX_COMBOS = 150
HOLDOUT_FRACTION = 0.2
DEFAULT_MIN_TRADES = 5
THRESHOLD_KEYS = frozenset({"buy_threshold", "sell_threshold"})
FILTER_KEYS = frozenset({
    "prob_smoothing_bars",
    "entry_confirmation_bars",
    "min_hold_bars",
    "cooldown_bars",
})
BLEND_KEYS = frozenset({"ou_ma_window", "adx_period", "adx_trend_threshold"})
ALLOWED_GRID_KEYS = (
    THRESHOLD_KEYS
    | FILTER_KEYS
    | BLEND_KEYS
    | {"num_paths", "calibration_years", "calibration_days"}
)
VALID_METRICS = frozenset({
    "sharpe_ratio",
    "sortino_ratio",
    "total_return",
    "excess_return",
    "max_drawdown",
    "win_rate",
    "profit_factor",
})

ProgressCallback = Callable[[int, int, str], Awaitable[None] | None]


@dataclass
class McBacktestOptimizationResult:
    best_params: dict
    best_metric: float
    best_avg_oos_max_drawdown: float | None
    all_results: list[dict]
    n_splits: int
    full_period_metrics: dict
    holdout_metrics: dict | None = None


def _normalize_threshold(value: float) -> float:
    return value / 100.0 if value > 1.0 else value


def _valid_threshold_order(buy: float, sell: float) -> bool:
    return sell < buy


def _normalize_combo_params(params: dict) -> dict:
    normalized = dict(params)
    for key in THRESHOLD_KEYS:
        if key in normalized:
            normalized[key] = _normalize_threshold(float(normalized[key]))
    for key in ("num_paths", "calibration_years", "calibration_days"):
        if key in normalized:
            normalized[key] = int(normalized[key])
    for key in FILTER_KEYS:
        if key in normalized:
            normalized[key] = int(normalized[key])
    return normalized


def _validate_filter_params(params: dict) -> None:
    checks = (
        ("prob_smoothing_bars", 0, 20),
        ("entry_confirmation_bars", 1, 10),
        ("min_hold_bars", 0, 50),
        ("cooldown_bars", 0, 50),
    )
    for key, lo, hi in checks:
        if key in params and not (lo <= params[key] <= hi):
            raise ValueError(f"{key} must be between {lo} and {hi}, got {params[key]}")


def validate_param_grid(param_grid: dict) -> list[dict]:
    if not param_grid:
        raise ValueError("param_grid must not be empty")
    unknown = set(param_grid.keys()) - ALLOWED_GRID_KEYS
    if unknown:
        raise ValueError(f"Unsupported param_grid keys: {sorted(unknown)}")

    raw_combos = generate_param_combinations(param_grid)
    combos = []
    for raw in raw_combos:
        params = _normalize_combo_params(raw)
        buy = params.get("buy_threshold", 0.65)
        sell = params.get("sell_threshold", 0.40)
        if not _valid_threshold_order(buy, sell):
            continue
        for key, lo, hi in (
            ("buy_threshold", 0.0, 1.0),
            ("sell_threshold", 0.0, 1.0),
        ):
            if key in params and not (lo <= params[key] <= hi):
                raise ValueError(f"{key} must be between 0 and 1 (or 0–100 as percent)")
        if "num_paths" in params and not (100 <= params["num_paths"] <= 5000):
            raise ValueError(f"num_paths must be between 100 and 5000, got {params['num_paths']}")
        if "calibration_years" in params and not (1 <= params["calibration_years"] <= 20):
            raise ValueError(
                f"calibration_years must be between 1 and 20, got {params['calibration_years']}"
            )
        if "calibration_days" in params and not (7 <= params["calibration_days"] <= 90):
            raise ValueError(
                f"calibration_days must be between 7 and 90, got {params['calibration_days']}"
            )
        _validate_filter_params(params)
        combos.append(params)

    if not combos:
        raise ValueError("No valid parameter combinations (check threshold order: sell < buy)")
    if len(combos) > MAX_COMBOS:
        raise ValueError(f"Too many combinations ({len(combos)}); max is {MAX_COMBOS}")
    return combos


def _build_config(
    params: dict,
    timeframe: str,
    model_type: str,
    start_date: datetime,
    end_date: datetime,
    defaults: dict,
    initial_capital: float,
) -> McBacktestConfig:
    cal_years = int(params.get("calibration_years", defaults.get("calibration_years", 10)))
    cal_days = params.get("calibration_days", defaults.get("calibration_days"))
    if cal_days is not None:
        cal_days = int(cal_days)
    return McBacktestConfig(
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        model_type=model_type,
        calibration_lookback_days=resolve_calibration_lookback_days(
            timeframe, cal_years, cal_days,
        ),
        num_paths=int(params.get("num_paths", defaults.get("num_paths", 500))),
        buy_threshold=float(params.get("buy_threshold", defaults.get("buy_threshold", 0.65))),
        sell_threshold=float(params.get("sell_threshold", defaults.get("sell_threshold", 0.40))),
        initial_capital=initial_capital,
        prob_smoothing_bars=int(
            params.get("prob_smoothing_bars", defaults.get("prob_smoothing_bars", 0)),
        ),
        entry_confirmation_bars=int(
            params.get("entry_confirmation_bars", defaults.get("entry_confirmation_bars", 1)),
        ),
        min_hold_bars=int(params.get("min_hold_bars", defaults.get("min_hold_bars", 0))),
        cooldown_bars=int(params.get("cooldown_bars", defaults.get("cooldown_bars", 0))),
        ou_ma_window=int(params.get("ou_ma_window", defaults.get("ou_ma_window", 20))),
        adx_period=int(params.get("adx_period", defaults.get("adx_period", 14))),
        adx_trend_threshold=float(
            params.get("adx_trend_threshold", defaults.get("adx_trend_threshold", 25.0)),
        ),
        regime_timeframe=defaults.get("regime_timeframe"),
        structure_timeframe=defaults.get("structure_timeframe"),
        mtf_gate_enabled=bool(defaults.get("mtf_gate_enabled", True)),
        regime_min_trend_weight=float(
            defaults.get("regime_min_trend_weight", 0.3),
        ),
        threshold_mode=defaults.get("threshold_mode", "static"),
        regime_mode=defaults.get("regime_mode", "adx"),
    )


def _metric_from_result(result, optimize_metric: str) -> float:
    if optimize_metric == "excess_return":
        return float(result.metrics.get("excess_return", -np.inf))
    metric_val = result.metrics.get(optimize_metric)
    if metric_val is None:
        return -np.inf
    return float(metric_val)


def _run_backtest_metrics(
    full_df: pd.DataFrame,
    config: McBacktestConfig,
    optimize_metric: str,
) -> tuple[float, float | None, int]:
    result = run_mc_backtest(full_df, config)
    metric_val = _metric_from_result(result, optimize_metric)
    drawdown = result.metrics.get("max_drawdown")
    num_trades = int(result.metrics.get("num_trades", 0))
    return metric_val, drawdown, num_trades


def compute_total_steps(n_combos: int, n_splits: int) -> int:
    """Train sweep + OOS eval per fold + final full-period + hold-out backtest."""
    return n_splits * (n_combos + 1) + 2


def _holdout_window(
    eval_df: pd.DataFrame,
    fraction: float = HOLDOUT_FRACTION,
) -> tuple[datetime, datetime] | None:
    n = len(eval_df)
    if n < 10:
        return None
    split_idx = int(n * (1 - fraction))
    if split_idx >= n - 1:
        return None
    start = pd.to_datetime(eval_df.iloc[split_idx]["time"]).to_pydatetime()
    end = pd.to_datetime(eval_df.iloc[-1]["time"]).to_pydatetime()
    return start, end


async def _run_backtest_metrics_async(
    full_df: pd.DataFrame,
    config: McBacktestConfig,
    optimize_metric: str,
) -> tuple[float, float | None, int]:
    return await asyncio.to_thread(_run_backtest_metrics, full_df, config, optimize_metric)


async def _emit_progress(
    on_progress: ProgressCallback | None,
    completed: int,
    total: int,
    message: str,
) -> None:
    if on_progress is not None:
        await on_progress(completed, total, message)


async def _pick_best_train_combo_async(
    full_df: pd.DataFrame,
    param_combos: list[dict],
    timeframe: str,
    model_type: str,
    train_start: datetime,
    train_end: datetime,
    defaults: dict,
    initial_capital: float,
    optimize_metric: str,
    fold_idx: int,
    n_splits: int,
    n_combos: int,
    completed: list[int],
    total: int,
    on_progress: ProgressCallback | None,
) -> int:
    best_metric = -np.inf
    best_idx = 0
    for combo_idx, params in enumerate(param_combos):
        try:
            config = _build_config(
                params, timeframe, model_type, train_start, train_end, defaults, initial_capital,
            )
            metric_val, _, _ = await _run_backtest_metrics_async(full_df, config, optimize_metric)
            completed[0] += 1
            await _emit_progress(
                on_progress,
                completed[0],
                total,
                f"Fold {fold_idx + 1}/{n_splits} — train combo {combo_idx + 1}/{n_combos}",
            )
            if metric_val > best_metric:
                best_metric = metric_val
                best_idx = combo_idx
        except Exception as exc:
            logger.warning("mc_bt_wfo_is_failed", fold=fold_idx, combo=params, error=str(exc))
    return best_idx


async def _record_oos_fold_async(
    full_df: pd.DataFrame,
    params: dict,
    timeframe: str,
    model_type: str,
    test_start: datetime,
    test_end: datetime,
    defaults: dict,
    initial_capital: float,
    optimize_metric: str,
    combo_idx: int,
    combo_scores: dict[int, list[float]],
    combo_oos_drawdowns: dict[int, list[float]],
    combo_oos_trades: dict[int, list[int]],
    fold_idx: int,
    n_splits: int,
    completed: list[int],
    total: int,
    on_progress: ProgressCallback | None,
) -> None:
    try:
        config = _build_config(
            params, timeframe, model_type, test_start, test_end, defaults, initial_capital,
        )
        metric_val, drawdown, num_trades = await _run_backtest_metrics_async(
            full_df, config, optimize_metric,
        )
        completed[0] += 1
        await _emit_progress(
            on_progress,
            completed[0],
            total,
            f"Fold {fold_idx + 1}/{n_splits} — OOS evaluation",
        )
        combo_scores[combo_idx].append(metric_val)
        combo_oos_drawdowns[combo_idx].append(drawdown if drawdown is not None else 0.0)
        combo_oos_trades[combo_idx].append(num_trades)
        logger.info(
            "mc_bt_wfo_fold_done",
            fold=fold_idx,
            params=params,
            oos_metric=round(metric_val, 4),
            oos_max_drawdown=round(drawdown or 0.0, 4),
            oos_trades=num_trades,
        )
    except Exception as exc:
        logger.warning("mc_bt_wfo_oos_failed", fold=fold_idx, error=str(exc))


async def walk_forward_mc_backtest_optimize_async(
    full_df: pd.DataFrame,
    param_grid: dict,
    n_splits: int,
    timeframe: str,
    model_type: str,
    eval_start: datetime,
    eval_end: datetime,
    optimize_metric: str,
    initial_capital: float = 1000.0,
    max_drawdown_cap: float | None = None,
    min_trades: int = DEFAULT_MIN_TRADES,
    defaults: dict | None = None,
    on_progress: ProgressCallback | None = None,
) -> McBacktestOptimizationResult:
    """Async walk-forward optimization with optional progress reporting."""
    if optimize_metric not in VALID_METRICS:
        raise ValueError(f"Unsupported optimize_metric: {optimize_metric}")

    defaults = defaults or {}
    param_combos = validate_param_grid(param_grid)
    work_df = full_df.sort_values("time").reset_index(drop=True)
    mask = (work_df["time"] >= eval_start) & (work_df["time"] <= eval_end)
    eval_df = work_df.loc[mask].reset_index(drop=True)
    splits = split_timeseries(eval_df, n_splits)
    if not splits:
        raise ValueError("Insufficient data for walk-forward optimization")

    n_combos = len(param_combos)
    total = compute_total_steps(n_combos, len(splits))
    completed = [0]
    combo_scores: dict[int, list[float]] = {i: [] for i in range(n_combos)}
    combo_oos_drawdowns: dict[int, list[float]] = {i: [] for i in range(n_combos)}
    combo_oos_trades: dict[int, list[int]] = {i: [] for i in range(n_combos)}

    logger.info(
        "mc_bt_wfo_start",
        n_combos=n_combos,
        n_splits=len(splits),
        optimize_metric=optimize_metric,
        min_trades=min_trades,
    )

    for fold_idx, (train_df, test_df) in enumerate(splits):
        train_start = pd.to_datetime(train_df.iloc[0]["time"]).to_pydatetime()
        train_end = pd.to_datetime(train_df.iloc[-1]["time"]).to_pydatetime()
        test_start = pd.to_datetime(test_df.iloc[0]["time"]).to_pydatetime()
        test_end = pd.to_datetime(test_df.iloc[-1]["time"]).to_pydatetime()

        best_idx = await _pick_best_train_combo_async(
            work_df,
            param_combos,
            timeframe,
            model_type,
            train_start,
            train_end,
            defaults,
            initial_capital,
            optimize_metric,
            fold_idx,
            len(splits),
            n_combos,
            completed,
            total,
            on_progress,
        )
        await _record_oos_fold_async(
            work_df,
            param_combos[best_idx],
            timeframe,
            model_type,
            test_start,
            test_end,
            defaults,
            initial_capital,
            optimize_metric,
            best_idx,
            combo_scores,
            combo_oos_drawdowns,
            combo_oos_trades,
            fold_idx,
            len(splits),
            completed,
            total,
            on_progress,
        )

    avg_scores, avg_drawdowns, avg_trades = _aggregate_combo_stats(
        combo_scores, combo_oos_drawdowns, combo_oos_trades,
    )
    best_idx = _select_best_combo(
        avg_scores,
        avg_drawdowns,
        avg_trades,
        combo_scores,
        max_drawdown_cap,
        optimize_metric,
        min_trades,
    )
    best_params = param_combos[best_idx]

    full_config = _build_config(
        best_params, timeframe, model_type, eval_start, eval_end, defaults, initial_capital,
    )
    full_result = await asyncio.to_thread(run_mc_backtest, work_df, full_config)
    completed[0] += 1
    await _emit_progress(on_progress, completed[0], total, "Final full-period backtest")

    holdout_metrics = None
    holdout_range = _holdout_window(eval_df)
    if holdout_range is not None:
        ho_start, ho_end = holdout_range
        holdout_config = _build_config(
            best_params, timeframe, model_type, ho_start, ho_end, defaults, initial_capital,
        )
        holdout_result = await asyncio.to_thread(run_mc_backtest, work_df, holdout_config)
        holdout_metrics = holdout_result.metrics
        completed[0] += 1
        await _emit_progress(on_progress, completed[0], total, "Hold-out period backtest")

    all_results = _build_sorted_results(param_combos, avg_scores, avg_drawdowns, avg_trades)

    return McBacktestOptimizationResult(
        best_params=best_params,
        best_metric=_safe_float(avg_scores[best_idx]),
        best_avg_oos_max_drawdown=avg_drawdowns[best_idx],
        all_results=all_results,
        n_splits=n_splits,
        full_period_metrics=full_result.metrics,
        holdout_metrics=holdout_metrics,
    )


def _pick_best_train_combo(
    full_df: pd.DataFrame,
    param_combos: list[dict],
    timeframe: str,
    model_type: str,
    train_start: datetime,
    train_end: datetime,
    defaults: dict,
    initial_capital: float,
    optimize_metric: str,
    fold_idx: int,
) -> int:
    best_metric = -np.inf
    best_idx = 0
    for combo_idx, params in enumerate(param_combos):
        try:
            config = _build_config(
                params, timeframe, model_type, train_start, train_end, defaults, initial_capital,
            )
            metric_val, _, _ = _run_backtest_metrics(full_df, config, optimize_metric)
            if metric_val > best_metric:
                best_metric = metric_val
                best_idx = combo_idx
        except Exception as exc:
            logger.warning("mc_bt_wfo_is_failed", fold=fold_idx, combo=params, error=str(exc))
    return best_idx


def _record_oos_fold(
    full_df: pd.DataFrame,
    params: dict,
    timeframe: str,
    model_type: str,
    test_start: datetime,
    test_end: datetime,
    defaults: dict,
    initial_capital: float,
    optimize_metric: str,
    combo_idx: int,
    combo_scores: dict[int, list[float]],
    combo_oos_drawdowns: dict[int, list[float]],
    combo_oos_trades: dict[int, list[int]],
    fold_idx: int,
) -> None:
    try:
        config = _build_config(
            params, timeframe, model_type, test_start, test_end, defaults, initial_capital,
        )
        metric_val, drawdown, num_trades = _run_backtest_metrics(full_df, config, optimize_metric)
        combo_scores[combo_idx].append(metric_val)
        combo_oos_drawdowns[combo_idx].append(drawdown if drawdown is not None else 0.0)
        combo_oos_trades[combo_idx].append(num_trades)
        logger.info(
            "mc_bt_wfo_fold_done",
            fold=fold_idx,
            params=params,
            oos_metric=round(metric_val, 4),
            oos_max_drawdown=round(drawdown or 0.0, 4),
            oos_trades=num_trades,
        )
    except Exception as exc:
        logger.warning("mc_bt_wfo_oos_failed", fold=fold_idx, error=str(exc))


def _aggregate_combo_stats(
    combo_scores: dict[int, list[float]],
    combo_oos_drawdowns: dict[int, list[float]],
    combo_oos_trades: dict[int, list[int]],
) -> tuple[dict[int, float], dict[int, float | None], dict[int, float]]:
    avg_scores = {
        idx: (_safe_float(np.mean(scores)) if scores else 0.0)
        for idx, scores in combo_scores.items()
    }
    avg_drawdowns = {
        idx: (_safe_float(np.mean(dds)) if dds else None)
        for idx, dds in combo_oos_drawdowns.items()
    }
    avg_trades = {
        idx: (_safe_float(np.mean(trades)) if trades else 0.0)
        for idx, trades in combo_oos_trades.items()
    }
    return avg_scores, avg_drawdowns, avg_trades


def _is_feasible(
    combo_idx: int,
    combo_scores: dict[int, list[float]],
    avg_drawdown: float | None,
    avg_trades: float,
    max_drawdown_cap: float | None,
    min_trades: int,
) -> bool:
    if not combo_scores[combo_idx]:
        return False
    if avg_trades < min_trades:
        return False
    if max_drawdown_cap is None:
        return True
    if avg_drawdown is None:
        return False
    return avg_drawdown >= max_drawdown_cap


def _select_best_combo(
    avg_scores: dict[int, float],
    avg_drawdowns: dict[int, float | None],
    avg_trades: dict[int, float],
    combo_scores: dict[int, list[float]],
    max_drawdown_cap: float | None,
    optimize_metric: str,
    min_trades: int,
) -> int:
    feasible = [
        idx for idx in avg_scores
        if _is_feasible(
            idx, combo_scores, avg_drawdowns[idx], avg_trades[idx],
            max_drawdown_cap, min_trades,
        )
    ]
    if not feasible:
        raise ValueError(NO_FEASIBLE_MSG)
    if optimize_metric == "max_drawdown":
        return max(feasible, key=lambda i: avg_scores[i])
    return max(feasible, key=lambda i: avg_scores[i])


def _build_sorted_results(
    param_combos: list[dict],
    avg_scores: dict[int, float],
    avg_drawdowns: dict[int, float | None],
    avg_trades: dict[int, float],
) -> list[dict]:
    results = [
        {
            "params": param_combos[i],
            "avg_oos_metric": avg_scores[i],
            "avg_oos_max_drawdown": avg_drawdowns[i],
            "avg_oos_trades": avg_trades[i],
        }
        for i in range(len(param_combos))
    ]
    return sorted(results, key=lambda r: r["avg_oos_metric"], reverse=True)


def max_fetch_lookback_days(
    timeframe: str,
    param_grid: dict,
    calibration_days: int | None = None,
) -> int:
    """Max OHLCV history needed for optimize job fetch."""
    if is_intraday_timeframe(timeframe):
        days_list = param_grid.get("calibration_days", [])
        if days_list:
            return max(int(v) for v in days_list)
        if calibration_days is not None:
            return int(calibration_days)
        return default_calibration_days(timeframe)
    years_list = param_grid.get("calibration_years", [10])
    return max(int(v) for v in years_list) * 365


def walk_forward_mc_backtest_optimize(
    full_df: pd.DataFrame,
    param_grid: dict,
    n_splits: int,
    timeframe: str,
    model_type: str,
    eval_start: datetime,
    eval_end: datetime,
    optimize_metric: str,
    initial_capital: float = 1000.0,
    max_drawdown_cap: float | None = None,
    min_trades: int = DEFAULT_MIN_TRADES,
    defaults: dict | None = None,
) -> McBacktestOptimizationResult:
    """Walk-forward optimization of MC backtest params (thresholds, paths, calibration)."""
    if optimize_metric not in VALID_METRICS:
        raise ValueError(f"Unsupported optimize_metric: {optimize_metric}")

    defaults = defaults or {}
    param_combos = validate_param_grid(param_grid)
    work_df = full_df.sort_values("time").reset_index(drop=True)
    mask = (work_df["time"] >= eval_start) & (work_df["time"] <= eval_end)
    eval_df = work_df.loc[mask].reset_index(drop=True)
    splits = split_timeseries(eval_df, n_splits)
    if not splits:
        raise ValueError("Insufficient data for walk-forward optimization")

    n_combos = len(param_combos)
    combo_scores: dict[int, list[float]] = {i: [] for i in range(n_combos)}
    combo_oos_drawdowns: dict[int, list[float]] = {i: [] for i in range(n_combos)}
    combo_oos_trades: dict[int, list[int]] = {i: [] for i in range(n_combos)}

    logger.info(
        "mc_bt_wfo_start",
        n_combos=n_combos,
        n_splits=len(splits),
        optimize_metric=optimize_metric,
        min_trades=min_trades,
    )

    for fold_idx, (train_df, test_df) in enumerate(splits):
        train_start = pd.to_datetime(train_df.iloc[0]["time"]).to_pydatetime()
        train_end = pd.to_datetime(train_df.iloc[-1]["time"]).to_pydatetime()
        test_start = pd.to_datetime(test_df.iloc[0]["time"]).to_pydatetime()
        test_end = pd.to_datetime(test_df.iloc[-1]["time"]).to_pydatetime()

        best_idx = _pick_best_train_combo(
            work_df,
            param_combos,
            timeframe,
            model_type,
            train_start,
            train_end,
            defaults,
            initial_capital,
            optimize_metric,
            fold_idx,
        )
        _record_oos_fold(
            work_df,
            param_combos[best_idx],
            timeframe,
            model_type,
            test_start,
            test_end,
            defaults,
            initial_capital,
            optimize_metric,
            best_idx,
            combo_scores,
            combo_oos_drawdowns,
            combo_oos_trades,
            fold_idx,
        )

    avg_scores, avg_drawdowns, avg_trades = _aggregate_combo_stats(
        combo_scores, combo_oos_drawdowns, combo_oos_trades,
    )
    best_idx = _select_best_combo(
        avg_scores,
        avg_drawdowns,
        avg_trades,
        combo_scores,
        max_drawdown_cap,
        optimize_metric,
        min_trades,
    )
    best_params = param_combos[best_idx]

    full_config = _build_config(
        best_params, timeframe, model_type, eval_start, eval_end, defaults, initial_capital,
    )
    full_result = run_mc_backtest(work_df, full_config)

    holdout_metrics = None
    holdout_range = _holdout_window(eval_df)
    if holdout_range is not None:
        ho_start, ho_end = holdout_range
        holdout_config = _build_config(
            best_params, timeframe, model_type, ho_start, ho_end, defaults, initial_capital,
        )
        holdout_metrics = run_mc_backtest(work_df, holdout_config).metrics

    all_results = _build_sorted_results(param_combos, avg_scores, avg_drawdowns, avg_trades)

    return McBacktestOptimizationResult(
        best_params=best_params,
        best_metric=_safe_float(avg_scores[best_idx]),
        best_avg_oos_max_drawdown=avg_drawdowns[best_idx],
        all_results=all_results,
        n_splits=n_splits,
        full_period_metrics=full_result.metrics,
        holdout_metrics=holdout_metrics,
    )
