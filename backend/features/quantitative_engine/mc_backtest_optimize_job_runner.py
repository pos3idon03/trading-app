"""Background job runner for MC backtest walk-forward optimization."""
import time
from datetime import datetime, timedelta

from dal.market_data_dal import get_ohlcv_with_resample
from dal.mc_backtest_optimize_job_dal import (
    get_job,
    mark_done,
    mark_error,
    mark_running,
    update_progress,
)
from db import AsyncSessionLocal
from dtos.backtest_dto import BacktestMetrics
from dtos.simulation_dto import McBacktestOptimizeSummary
from features.quantitative_engine.mc_backtest_optimizer import (
    compute_total_steps,
    max_fetch_lookback_days,
    validate_param_grid,
    walk_forward_mc_backtest_optimize_async,
)
from features.quantitative_engine.mc_intraday import (
    intraday_ohlcv_error_message,
    is_intraday_timeframe,
)
from utils.logging import get_logger

logger = get_logger(__name__)


def _parse_request_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _build_result_dict(
    asset_id: int,
    symbol: str,
    optimize_metric: str,
    result,
    duration_ms: int,
) -> dict:
    return {
        "asset_id": asset_id,
        "symbol": symbol,
        "status": "done",
        "optimize_metric": optimize_metric,
        "n_splits": result.n_splits,
        "best_params": result.best_params,
        "best_metric": result.best_metric,
        "best_avg_oos_max_drawdown": result.best_avg_oos_max_drawdown,
        "all_results": [
            McBacktestOptimizeSummary(**r).model_dump(mode="json") for r in result.all_results
        ],
        "full_period_metrics": BacktestMetrics(**result.full_period_metrics).model_dump(mode="json"),
        "holdout_metrics": (
            BacktestMetrics(**result.holdout_metrics).model_dump(mode="json")
            if result.holdout_metrics
            else None
        ),
        "duration_ms": duration_ms,
    }


async def run_mc_backtest_optimize_job(job_id: int) -> None:
    """Execute a pending MC backtest optimize job in the background."""
    t0 = time.perf_counter()
    async with AsyncSessionLocal() as session:
        job = await get_job(session, job_id)
        if job is None:
            logger.error("mc_bt_opt_job_not_found", job_id=job_id)
            return

        req = job.request
        asset_id = int(req["asset_id"])
        symbol = job.symbol
        timeframe = req["timeframe"]
        start_date = _parse_request_datetime(req["start_date"])
        end_date = _parse_request_datetime(req["end_date"])
        model_type = req["model_type"]
        param_grid = req["param_grid"]
        n_splits = int(req["n_splits"])
        optimize_metric = req["optimize_metric"]
        initial_capital = float(req.get("initial_capital", 1000.0))
        max_drawdown_cap = req.get("max_drawdown_cap")
        calibration_days = req.get("calibration_days")
        min_trades = int(req.get("min_trades", 5))

        try:
            param_combos = validate_param_grid(param_grid)
            total_steps = compute_total_steps(len(param_combos), n_splits)
            await mark_running(session, job_id, total_steps)
            await session.commit()

            lookback_days = max_fetch_lookback_days(
                timeframe, param_grid, calibration_days,
            )
            fetch_start = start_date - timedelta(days=lookback_days)

            df = await get_ohlcv_with_resample(session, asset_id, timeframe, fetch_start, end_date)
            if df.empty:
                if is_intraday_timeframe(timeframe):
                    raise ValueError(intraday_ohlcv_error_message(timeframe, symbol))
                raise ValueError(f"No {timeframe} price data available for {symbol}.")

            defaults: dict = {}
            if calibration_days is not None:
                defaults["calibration_days"] = int(calibration_days)

            async def on_progress(completed: int, total: int, message: str) -> None:
                await update_progress(session, job_id, completed, total, message)
                await session.commit()

            result = await walk_forward_mc_backtest_optimize_async(
                df,
                param_grid=param_grid,
                n_splits=n_splits,
                timeframe=timeframe,
                model_type=model_type,
                eval_start=start_date,
                eval_end=end_date,
                optimize_metric=optimize_metric,
                initial_capital=initial_capital,
                max_drawdown_cap=max_drawdown_cap,
                min_trades=min_trades,
                defaults=defaults,
                on_progress=on_progress,
            )
            duration_ms = int((time.perf_counter() - t0) * 1000)
            result_dict = _build_result_dict(
                asset_id, symbol, optimize_metric, result, duration_ms,
            )
            await mark_done(session, job_id, result_dict, duration_ms)
            await session.commit()
            logger.info("mc_bt_opt_job_done", job_id=job_id, duration_ms=duration_ms)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            logger.error("mc_bt_opt_job_failed", job_id=job_id, error=str(exc))
            await mark_error(session, job_id, str(exc), duration_ms)
            await session.commit()
