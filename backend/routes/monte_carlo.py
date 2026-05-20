"""Monte Carlo simulation API routes."""
import asyncio
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_asset_id_by_symbol, get_ohlcv, get_ohlcv_with_resample
from dal.mc_backtest_optimize_job_dal import create_job, get_job
from dal.simulation_dal import create_simulation, get_simulation, update_simulation_result
from db import get_db
from dtos.backtest_dto import BacktestMetrics
from dtos.simulation_dto import (
    CalibrationRequest,
    CalibrationResponse,
    DistributionPoint,
    McBacktestExecutionEvent,
    McBacktestOptimizeJobStartResponse,
    McBacktestOptimizeJobStatusResponse,
    McBacktestOptimizeRequest,
    McBacktestOptimizeResponse,
    McBacktestOptimizeSummary,
    McBacktestRequest,
    McBacktestResponse,
    McBacktestSignalPoint,
    McBacktestZoneStats,
    McSimulationOptimizeRequest,
    McSimulationOptimizeResponse,
    McSimulationOptimizeSummary,
    ReturnDistribution,
    SimulationRequest,
    SimulationResponse,
    SimulationStats,
)
from features.quantitative_engine.calibration_service import calibrate_model_for_asset
from features.quantitative_engine.mc_backtest import (
    McBacktestConfig,
    mc_config_from_request,
    run_mc_backtest,
)
from features.quantitative_engine.mc_feature_export import export_backtest_features
from features.quantitative_engine.mc_mtf import mc_data_load_timeframe
from features.quantitative_engine.mc_combo import AlgoComboLeg
from features.quantitative_engine.mc_backtest_optimize_job_runner import run_mc_backtest_optimize_job
from features.quantitative_engine.mc_backtest_optimizer import (
    max_fetch_lookback_days,
    validate_param_grid,
)
from features.quantitative_engine.mc_intraday import (
    intraday_ohlcv_error_message,
    is_intraday_timeframe,
    resolve_calibration_lookback_days,
)
from features.quantitative_engine.mc_simulation_optimizer import (
    run_best_params_simulation,
    walk_forward_mc_simulation_optimize,
)
from features.quantitative_engine.monte_carlo import compute_return_distribution
from features.quantitative_engine.simulation_runner import dispatch_mc_simulation, timeframe_to_dt, adx_from_ohlcv
from features.quantitative_engine.vasicek import VasicekParams as VasicekInternal
from features.quantitative_engine.jump_diffusion import JumpParams as JumpInternal, JumpDistParams
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/calibrate/{asset_id}", response_model=CalibrationResponse)
async def calibrate_model(
    asset_id: int,
    request: CalibrationRequest,
    session: AsyncSession = Depends(get_db),
) -> CalibrationResponse:
    """Calibrate Vasicek+Jump parameters for an asset using stored OHLCV data."""
    try:
        params = await calibrate_model_for_asset(
            session,
            asset_id=asset_id,
            timeframe=request.timeframe,
            start=request.start_date,
            end=request.end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("calibration_error", asset_id=asset_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return CalibrationResponse(
        asset_id=asset_id,
        symbol="",
        params=params,
        message="Calibration completed successfully",
    )


@router.post("/run", response_model=SimulationResponse, status_code=202)
async def run_monte_carlo(
    request: SimulationRequest,
    session: AsyncSession = Depends(get_db),
) -> SimulationResponse:
    """Execute a Monte Carlo simulation for an asset."""
    asset_id = await _resolve_asset_id(session, request.asset_id, request.symbol)

    if request.use_stored_params:
        try:
            calibrated = await calibrate_model_for_asset(
                session,
                asset_id=asset_id,
                timeframe=request.timeframe,
                calibration_years=request.calibration_years,
                ou_ma_window=request.ou_ma_window,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    elif request.custom_params:
        calibrated = request.custom_params
    else:
        raise HTTPException(status_code=400, detail="Provide custom_params or set use_stored_params=true")

    dt = timeframe_to_dt(request.timeframe)
    params_dict = calibrated.model_dump(mode="json")

    s0 = calibrated.last_price

    sim_id = await create_simulation(
        session,
        asset_id=asset_id,
        timeframe=request.timeframe,
        params=params_dict,
        num_paths=request.num_paths,
        horizon_steps=request.horizon_steps,
        dt=dt,
        s0=s0,
        calibration_start=calibrated.calibration_start,
        calibration_end=calibrated.calibration_end,
    )

    try:
        adx_val = None
        if request.model_type == "blended":
            cal_start = calibrated.calibration_start
            cal_end = calibrated.calibration_end
            ohlcv = await get_ohlcv(session, asset_id, request.timeframe, cal_start, cal_end)
            adx_val = adx_from_ohlcv(ohlcv, request.adx_period)

        result = dispatch_mc_simulation(
            calibrated,
            request.model_type,
            request.num_paths,
            request.horizon_steps,
            request.timeframe,
            adx=adx_val,
            adx_trend_threshold=request.adx_trend_threshold,
        )
        stats = result.stats

        await update_simulation_result(
            session,
            sim_id=sim_id,
            result_summary=_stats_to_dict(stats),
            percentile_paths=result.percentile_paths,
            duration_ms=int(result.duration_ms),
        )

        return_dist = None
        if request.include_distribution:
            jumps = _to_internal_jumps(calibrated.jumps)
            vasicek_for_dist = _to_internal_vasicek(calibrated.vasicek)
            return_dist = _build_return_distribution(result.paths, vasicek_for_dist, jumps)

        return SimulationResponse(
            simulation_id=sim_id,
            asset_id=asset_id,
            status="done",
            params=params_dict,
            stats=SimulationStats(**_stats_to_dict(stats)),
            percentile_paths=result.percentile_paths,
            duration_ms=int(result.duration_ms),
            return_distribution=return_dist,
        )
    except Exception as exc:
        logger.error("simulation_run_error", sim_id=sim_id, error=str(exc))
        await update_simulation_result(session, sim_id, {}, {}, 0, status="error", error_message=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/backtest", response_model=McBacktestResponse)
async def execute_mc_backtest(
    request: McBacktestRequest,
    session: AsyncSession = Depends(get_db),
) -> McBacktestResponse:
    """Walk-forward MC backtest using prob-positive thresholds."""
    asset_id = await _resolve_asset_id(session, request.asset_id, request.symbol)
    symbol = request.symbol or str(asset_id)

    lookback_days = resolve_calibration_lookback_days(
        request.timeframe,
        request.calibration_years,
        request.calibration_days,
    )
    load_tf = mc_data_load_timeframe(
        request.timeframe,
        request.regime_timeframe,
        request.structure_timeframe,
    )
    fetch_start = request.start_date - timedelta(days=lookback_days)
    try:
        df = await get_ohlcv_with_resample(
            session, asset_id, load_tf, fetch_start, request.end_date,
        )
        if df.empty:
            if is_intraday_timeframe(request.timeframe):
                raise ValueError(intraday_ohlcv_error_message(request.timeframe, symbol))
            raise ValueError("No OHLCV data for the requested period")

        algo_legs = [
            AlgoComboLeg(
                strategy_name=leg.strategy_name,
                strategy_params=leg.strategy_params,
                weight=leg.weight,
                timeframe=leg.timeframe,
            )
            for leg in request.algo_strategies
        ] if request.combo_enabled else None
        config = mc_config_from_request(request, lookback_days, algo_legs)
        result = run_mc_backtest(df, config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("mc_backtest_error", asset_id=asset_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return McBacktestResponse(
        asset_id=asset_id,
        symbol=symbol,
        status="done",
        metrics=BacktestMetrics(**result.metrics),
        equity_curve=result.equity_curve,
        buy_hold_curve=result.buy_hold_curve,
        trade_log=result.trade_log,
        execution_log=[McBacktestExecutionEvent(**e) for e in result.execution_log],
        signal_log=[McBacktestSignalPoint(**s) for s in result.signal_log],
        zone_stats=McBacktestZoneStats(**result.zone_stats) if result.zone_stats else None,
        combo_signals=result.combo_signals or [],
        combined_signal_timeline=result.combined_signal_timeline or [],
        bars_evaluated=result.bars_evaluated,
        duration_ms=int(result.duration_ms),
    )


@router.post("/backtest/export-features")
async def export_mc_backtest_features(
    request: McBacktestRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Walk-forward feature export for offline ML training (train_models.py)."""
    from pathlib import Path

    asset_id = await _resolve_asset_id(session, request.asset_id, request.symbol)
    lookback_days = resolve_calibration_lookback_days(
        request.timeframe,
        request.calibration_years,
        request.calibration_days,
    )
    load_tf = mc_data_load_timeframe(
        request.timeframe,
        request.regime_timeframe,
        request.structure_timeframe,
    )
    fetch_start = request.start_date - timedelta(days=lookback_days)
    df = await get_ohlcv_with_resample(
        session, asset_id, load_tf, fetch_start, request.end_date,
    )
    if df.empty:
        raise HTTPException(status_code=422, detail="No OHLCV data for feature export")

    algo_legs = None
    config = mc_config_from_request(request, lookback_days, algo_legs)
    out_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "mc_ml_models"
        / f"features_{asset_id}_{request.timeframe}.csv"
    )
    rows = export_backtest_features(df, config, out_path)
    return {"rows": rows, "path": str(out_path), "asset_id": asset_id}


@router.post(
    "/backtest/optimize",
    response_model=McBacktestOptimizeJobStartResponse,
    status_code=202,
)
async def optimize_mc_backtest(
    request: McBacktestOptimizeRequest,
    session: AsyncSession = Depends(get_db),
) -> McBacktestOptimizeJobStartResponse:
    """Start a background walk-forward optimization of MC backtest params."""
    asset_id = await _resolve_asset_id(session, request.asset_id, request.symbol)
    symbol = request.symbol or str(asset_id)

    try:
        validate_param_grid(request.param_grid)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    cal_years_list = request.param_grid.get("calibration_years", [10])
    lookback_days = max_fetch_lookback_days(
        request.timeframe,
        request.param_grid,
        request.calibration_days,
    )
    fetch_start = request.start_date - timedelta(days=lookback_days)

    df = await get_ohlcv_with_resample(
        session, asset_id, request.timeframe, fetch_start, request.end_date,
    )
    if df.empty:
        if is_intraday_timeframe(request.timeframe):
            raise HTTPException(
                status_code=404,
                detail=intraday_ohlcv_error_message(request.timeframe, symbol),
            )
        raise HTTPException(
            status_code=404,
            detail=f"No {request.timeframe} price data available for {symbol}.",
        )

    eval_mask = (df["time"] >= request.start_date) & (df["time"] <= request.end_date)
    eval_rows = int(eval_mask.sum())
    min_rows = (request.n_splits + 1) * 30
    if eval_rows < min_rows:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Insufficient data for walk-forward optimization: {eval_rows} rows "
                f"in range (need {min_rows})"
            ),
        )

    request_dict = request.model_dump(mode="json")
    request_dict["asset_id"] = asset_id
    job_id = await create_job(session, asset_id, symbol, request_dict)
    await session.commit()
    asyncio.create_task(run_mc_backtest_optimize_job(job_id))

    return McBacktestOptimizeJobStartResponse(job_id=job_id, status="pending")


@router.get(
    "/backtest/optimize/jobs/{job_id}",
    response_model=McBacktestOptimizeJobStatusResponse,
)
async def get_mc_backtest_optimize_job(
    job_id: int,
    session: AsyncSession = Depends(get_db),
) -> McBacktestOptimizeJobStatusResponse:
    """Poll status and results for an MC backtest optimize job."""
    job = await get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Optimize job {job_id} not found")
    return _job_to_status_response(job)


def _job_to_status_response(job) -> McBacktestOptimizeJobStatusResponse:
    req = job.request
    optimize_metric = req.get("optimize_metric", "sharpe_ratio")
    n_splits = int(req.get("n_splits", 5))
    base = {
        "job_id": job.id,
        "asset_id": job.asset_id,
        "symbol": job.symbol,
        "status": job.status,
        "optimize_metric": optimize_metric,
        "n_splits": n_splits,
        "progress_pct": job.progress_pct,
        "progress_message": job.progress_message,
        "completed_steps": job.completed_steps,
        "total_steps": job.total_steps,
        "duration_ms": job.duration_ms or 0,
        "error_message": job.error_message,
    }
    if job.status == "done" and job.result:
        result = job.result
        return McBacktestOptimizeJobStatusResponse(
            **base,
            best_params=result.get("best_params"),
            best_metric=result.get("best_metric"),
            best_avg_oos_max_drawdown=result.get("best_avg_oos_max_drawdown"),
            all_results=[
                McBacktestOptimizeSummary(**r) for r in (result.get("all_results") or [])
            ],
            full_period_metrics=(
                BacktestMetrics(**result["full_period_metrics"])
                if result.get("full_period_metrics")
                else None
            ),
            holdout_metrics=(
                BacktestMetrics(**result["holdout_metrics"])
                if result.get("holdout_metrics")
                else None
            ),
            duration_ms=result.get("duration_ms", job.duration_ms or 0),
        )
    return McBacktestOptimizeJobStatusResponse(**base)


@router.post("/optimize", response_model=McSimulationOptimizeResponse)
async def optimize_mc_simulation(
    request: McSimulationOptimizeRequest,
    session: AsyncSession = Depends(get_db),
) -> McSimulationOptimizeResponse:
    """Walk-forward optimization of MC simulation config params."""
    asset_id = await _resolve_asset_id(session, request.asset_id, request.symbol)
    symbol = request.symbol or str(asset_id)

    df = await get_ohlcv(
        session, asset_id, request.timeframe, request.start_date, request.end_date,
    )
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No {request.timeframe} price data available for {symbol}.",
        )

    min_rows = (request.n_splits + 1) * 30
    if len(df) < min_rows:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Insufficient data for walk-forward optimization: {len(df)} rows "
                f"in range (need {min_rows})"
            ),
        )

    t0 = time.perf_counter()
    try:
        result = walk_forward_mc_simulation_optimize(
            df,
            param_grid=request.param_grid,
            n_splits=request.n_splits,
            model_type=request.model_type,
            timeframe=request.timeframe,
            horizon_steps=request.horizon_steps,
            optimize_metric=request.optimize_metric,
            max_drawdown_cap=request.max_drawdown_cap,
        )
        best_run = run_best_params_simulation(
            df,
            result.best_params,
            request.model_type,
            request.timeframe,
            request.horizon_steps,
        )
        duration_ms = int((time.perf_counter() - t0) * 1000)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("mc_sim_optimize_error", asset_id=asset_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return McSimulationOptimizeResponse(
        asset_id=asset_id,
        symbol=symbol,
        status="done",
        optimize_metric=request.optimize_metric,
        n_splits=result.n_splits,
        best_params=result.best_params,
        best_metric=result.best_metric,
        best_avg_oos_max_drawdown=result.best_avg_oos_max_drawdown,
        all_results=[McSimulationOptimizeSummary(**r) for r in result.all_results],
        best_run_stats=SimulationStats(**_stats_to_dict(best_run.stats)),
        best_run_percentile_paths=best_run.percentile_paths,
        duration_ms=duration_ms,
    )


@router.get("/{sim_id}", response_model=SimulationResponse)
async def get_simulation_result(
    sim_id: int,
    session: AsyncSession = Depends(get_db),
) -> SimulationResponse:
    """Retrieve a stored simulation result."""
    sim = await get_simulation(session, sim_id)
    if sim is None:
        raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")

    stats = SimulationStats(**sim.result_summary) if sim.result_summary else None
    return SimulationResponse(
        simulation_id=sim.id,
        asset_id=sim.asset_id,
        status=sim.status,
        params=sim.params,
        stats=stats,
        percentile_paths=sim.percentile_paths,
        duration_ms=sim.duration_ms,
    )


def _to_internal_vasicek(dto) -> VasicekInternal:
    return VasicekInternal(k=dto.k, theta=dto.theta, sigma=dto.sigma, mu=dto.mu)


def _to_internal_jumps(dto) -> JumpInternal:
    return JumpInternal(
        lambda_up=dto.lambda_up,
        lambda_down=dto.lambda_down,
        up=JumpDistParams(mu=dto.mu_up, sigma=dto.sigma_up),
        down=JumpDistParams(mu=dto.mu_down, sigma=dto.sigma_down),
    )


def _stats_to_dict(stats) -> dict:
    return {
        "mean_terminal": stats.mean_terminal,
        "std_terminal": stats.std_terminal,
        "p5": stats.p5,
        "p25": stats.p25,
        "p50": stats.p50,
        "p75": stats.p75,
        "p95": stats.p95,
        "prob_positive_return": stats.prob_positive_return,
        "mean_max_drawdown": stats.mean_max_drawdown,
    }


def _build_return_distribution(paths, vasicek, jumps) -> ReturnDistribution:
    """Convert internal DistributionData into the API DTO."""
    dist = compute_return_distribution(paths, vasicek, jumps)
    return ReturnDistribution(
        histogram=[DistributionPoint(x=x, density=d) for x, d in dist.histogram],
        mr_density=[DistributionPoint(x=x, density=d) for x, d in dist.mr_density],
        jump_up_density=[DistributionPoint(x=x, density=d) for x, d in dist.jump_up_density],
        jump_down_density=[DistributionPoint(x=x, density=d) for x, d in dist.jump_down_density],
    )


async def _resolve_asset_id(
    session: AsyncSession,
    asset_id: int | None,
    symbol: str | None,
) -> int:
    if asset_id is not None:
        return asset_id
    resolved = await get_asset_id_by_symbol(session, symbol)
    if resolved is None:
        raise HTTPException(status_code=404, detail=f"Asset '{symbol}' not found")
    return resolved
