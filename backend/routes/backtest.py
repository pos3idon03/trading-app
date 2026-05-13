"""Backtesting API routes."""
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_asset_id_by_symbol, get_ohlcv
from dal.simulation_dal import (
    create_backtest,
    create_optimization,
    get_backtest,
    get_optimization,
    get_simulation,
    update_backtest_result,
    update_optimization_result,
)
from db import get_db
from dtos.backtest_dto import (
    BacktestMetrics,
    BacktestRequest,
    BacktestResponse,
    ComboBacktestRequest,
    OptimizationRequest,
    OptimizationResponse,
    OptimizationSummary,
)
from features.backtesting.combo_runner import ComboStrategyConfig, run_combo_backtest
from features.backtesting.indicator_snapshot import compute_monthly_breakdown
from features.backtesting.optimizer import walk_forward_optimize
from features.backtesting.runner import prepare_simulated_dataframe, run_backtest
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/run", response_model=BacktestResponse, status_code=202)
async def execute_backtest(
    request: BacktestRequest,
    session: AsyncSession = Depends(get_db),
) -> BacktestResponse:
    """Execute a backtest for an asset with a specified strategy and date range.

    Accepts either historical OHLCV data (via asset_id/symbol) or Monte Carlo
    simulated paths (via simulation_id).
    """
    if request.simulation_id is not None:
        return await _run_simulated_backtest(session, request)
    return await _run_historical_backtest(session, request)


@router.get("/{bt_id}/results", response_model=BacktestResponse)
async def get_backtest_results(
    bt_id: int,
    session: AsyncSession = Depends(get_db),
) -> BacktestResponse:
    """Retrieve stored backtest results."""
    bt = await get_backtest(session, bt_id)
    if bt is None:
        raise HTTPException(status_code=404, detail=f"Backtest {bt_id} not found")

    metrics = _build_metrics(bt) if bt.status == "done" else None

    return BacktestResponse(
        backtest_id=bt.id,
        asset_id=bt.asset_id,
        strategy_name=bt.strategy_name,
        status=bt.status,
        metrics=metrics,
        equity_curve=bt.equity_curve,
        trade_log=bt.trade_log,
        buy_hold_curve=bt.buy_hold_curve,
        duration_ms=bt.duration_ms,
        error_message=bt.error_message,
    )


@router.post("/combo", response_model=BacktestResponse, status_code=202)
async def execute_combo_backtest(
    request: ComboBacktestRequest,
    session: AsyncSession = Depends(get_db),
) -> BacktestResponse:
    """Execute a combination backtest that merges signals from 2+ strategies.

    Supports AND (unanimous), majority voting, and weighted-threshold modes.
    """
    if request.simulation_id is not None:
        return await _run_combo_simulated(session, request)
    return await _run_combo_historical(session, request)


async def _run_combo_historical(
    session: AsyncSession,
    request: ComboBacktestRequest,
) -> BacktestResponse:
    asset_id = await _resolve_asset_id(session, request.asset_id, request.symbol)

    df = await get_ohlcv(
        session,
        asset_id=asset_id,
        start=request.start_date,
        end=request.end_date,
        **_ohlcv_query_args(request.timeframe),
    )

    if df.empty or len(df) < 20:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient data for combo backtest: {len(df)} rows",
        )

    return await _execute_and_persist_combo(session, request, df, asset_id)


async def _run_combo_simulated(
    session: AsyncSession,
    request: ComboBacktestRequest,
) -> BacktestResponse:
    sim = await get_simulation(session, request.simulation_id)
    if sim is None:
        raise HTTPException(
            status_code=404, detail=f"Simulation {request.simulation_id} not found"
        )
    if sim.status != "done":
        raise HTTPException(
            status_code=422,
            detail=f"Simulation {request.simulation_id} is not completed (status: {sim.status})",
        )

    try:
        df = prepare_simulated_dataframe(sim)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if len(df) < 20:
        raise HTTPException(
            status_code=422,
            detail=f"Simulated path too short for combo backtest: {len(df)} rows",
        )

    return await _execute_and_persist_combo(session, request, df, sim.asset_id)


def _build_combo_strategy_name(request: ComboBacktestRequest) -> str:
    return f"combo:{request.combination_mode}"


def _build_combo_params(request: ComboBacktestRequest) -> dict:
    return {
        "combination_mode": request.combination_mode,
        "threshold": request.threshold,
        "strategies": [
            {
                "strategy_name": s.strategy_name,
                "strategy_params": s.strategy_params,
                "weight": s.weight,
            }
            for s in request.strategies
        ],
    }


async def _execute_and_persist_combo(
    session: AsyncSession,
    request: ComboBacktestRequest,
    df,
    asset_id: int,
) -> BacktestResponse:
    strategy_name = _build_combo_strategy_name(request)
    params = _build_combo_params(request)

    bt_id = await create_backtest(
        session,
        asset_id=asset_id,
        strategy_name=strategy_name,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        params=params,
    )

    configs = [
        ComboStrategyConfig(
            strategy_name=s.strategy_name,
            strategy_params=s.strategy_params,
            weight=s.weight,
        )
        for s in request.strategies
    ]

    try:
        result = run_combo_backtest(
            df,
            strategies=configs,
            combination_mode=request.combination_mode,
            threshold=request.threshold,
            initial_capital=request.initial_capital,
            timeframe=request.timeframe,
        )

        monthly_breakdown = compute_monthly_breakdown(
            df,
            strategies=configs,
            mode=request.combination_mode,
            threshold=request.threshold,
        )

        await update_backtest_result(
            session,
            bt_id=bt_id,
            metrics=result.metrics,
            equity_curve=result.equity_curve,
            trade_log=result.trade_log,
            duration_ms=int(result.duration_ms),
            buy_hold_curve=result.buy_hold_curve,
        )

        return BacktestResponse(
            backtest_id=bt_id,
            asset_id=asset_id,
            strategy_name=strategy_name,
            status="done",
            metrics=BacktestMetrics(**result.metrics),
            equity_curve=result.equity_curve,
            trade_log=result.trade_log,
            buy_hold_curve=result.buy_hold_curve,
            duration_ms=int(result.duration_ms),
            monthly_breakdown=monthly_breakdown,
        )
    except Exception as exc:
        logger.error("combo_backtest_error", bt_id=bt_id, error=str(exc))
        await update_backtest_result(
            session, bt_id, {}, [], [], 0, status="error", error_message=str(exc)
        )
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/optimize", response_model=OptimizationResponse, status_code=202)
async def run_optimization(
    request: OptimizationRequest,
    session: AsyncSession = Depends(get_db),
) -> OptimizationResponse:
    """Walk-forward parameter optimization for a strategy over historical data."""
    asset_id = await _resolve_asset_id(session, request.asset_id, request.symbol)

    df = await get_ohlcv(
        session,
        asset_id=asset_id,
        timeframe=request.timeframe,
        start=request.start_date,
        end=request.end_date,
    )

    min_rows = (request.n_splits + 1) * 30
    if df.empty or len(df) < min_rows:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient data for walk-forward optimization: {len(df)} rows (need {min_rows})",
        )

    opt_id = await create_optimization(
        session,
        asset_id=asset_id,
        strategy_name=request.strategy_name,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        param_grid=request.param_grid,
        n_splits=request.n_splits,
        optimize_metric=request.optimize_metric,
    )

    t0 = time.perf_counter()
    try:
        result = walk_forward_optimize(
            df,
            strategy=request.strategy_name,
            param_grid=request.param_grid,
            n_splits=request.n_splits,
            initial_capital=request.initial_capital,
            optimize_metric=request.optimize_metric,
        )
        duration_ms = int((time.perf_counter() - t0) * 1000)

        await update_optimization_result(
            session,
            opt_id=opt_id,
            best_params=result.best_params,
            best_metric=result.best_sharpe,
            all_results=result.all_results,
            duration_ms=duration_ms,
        )

        return OptimizationResponse(
            optimization_id=opt_id,
            asset_id=asset_id,
            strategy_name=request.strategy_name,
            status="done",
            optimize_metric=request.optimize_metric,
            n_splits=result.n_splits,
            best_params=result.best_params,
            best_metric=result.best_sharpe,
            all_results=[OptimizationSummary(**r) for r in result.all_results],
            duration_ms=duration_ms,
        )
    except Exception as exc:
        logger.error("optimization_error", opt_id=opt_id, error=str(exc))
        duration_ms = int((time.perf_counter() - t0) * 1000)
        await update_optimization_result(
            session, opt_id, {}, 0.0, [], duration_ms, status="error", error_message=str(exc)
        )
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{opt_id}/optimization", response_model=OptimizationResponse)
async def get_optimization_results(
    opt_id: int,
    session: AsyncSession = Depends(get_db),
) -> OptimizationResponse:
    """Retrieve stored walk-forward optimization results."""
    opt = await get_optimization(session, opt_id)
    if opt is None:
        raise HTTPException(status_code=404, detail=f"OptimizationRun {opt_id} not found")

    all_results = None
    if opt.all_results:
        all_results = [OptimizationSummary(**r) for r in opt.all_results]

    return OptimizationResponse(
        optimization_id=opt.id,
        asset_id=opt.asset_id,
        strategy_name=opt.strategy_name,
        status=opt.status,
        optimize_metric=opt.optimize_metric,
        n_splits=opt.n_splits,
        best_params=opt.best_params,
        best_metric=opt.best_metric,
        all_results=all_results,
        duration_ms=opt.duration_ms,
        error_message=opt.error_message,
    )


def _ohlcv_query_args(timeframe: str) -> dict:
    """Return get_ohlcv keyword args for the given timeframe.

    Weekly backtests resample stored daily bars via TimescaleDB time_bucket.
    asyncpg requires a timedelta for interval parameters, not a plain string.
    """
    if timeframe == "1w":
        return {"timeframe": "1d", "bucket_interval": timedelta(weeks=1)}
    return {"timeframe": timeframe}


async def _run_historical_backtest(
    session: AsyncSession,
    request: BacktestRequest,
) -> BacktestResponse:
    asset_id = await _resolve_asset_id(session, request.asset_id, request.symbol)

    df = await get_ohlcv(
        session,
        asset_id=asset_id,
        start=request.start_date,
        end=request.end_date,
        **_ohlcv_query_args(request.timeframe),
    )

    if df.empty or len(df) < 20:
        raise HTTPException(status_code=422, detail=f"Insufficient data for backtest: {len(df)} rows")

    return await _execute_and_persist_backtest(session, request, df, asset_id)


async def _run_simulated_backtest(
    session: AsyncSession,
    request: BacktestRequest,
) -> BacktestResponse:
    sim = await get_simulation(session, request.simulation_id)
    if sim is None:
        raise HTTPException(status_code=404, detail=f"Simulation {request.simulation_id} not found")
    if sim.status != "done":
        raise HTTPException(status_code=422, detail=f"Simulation {request.simulation_id} is not completed (status: {sim.status})")

    try:
        df = prepare_simulated_dataframe(sim)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if len(df) < 20:
        raise HTTPException(status_code=422, detail=f"Simulated path too short for backtest: {len(df)} rows")

    return await _execute_and_persist_backtest(session, request, df, sim.asset_id)


async def _execute_and_persist_backtest(
    session: AsyncSession,
    request: BacktestRequest,
    df,
    asset_id: int,
) -> BacktestResponse:
    bt_id = await create_backtest(
        session,
        asset_id=asset_id,
        strategy_name=request.strategy_name,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        params=request.strategy_params,
    )

    try:
        result = run_backtest(
            df,
            strategy=request.strategy_name,
            params=request.strategy_params,
            initial_capital=request.initial_capital,
            timeframe=request.timeframe,
        )

        await update_backtest_result(
            session,
            bt_id=bt_id,
            metrics=result.metrics,
            equity_curve=result.equity_curve,
            trade_log=result.trade_log,
            duration_ms=int(result.duration_ms),
            buy_hold_curve=result.buy_hold_curve,
        )

        return BacktestResponse(
            backtest_id=bt_id,
            asset_id=asset_id,
            strategy_name=request.strategy_name,
            status="done",
            metrics=BacktestMetrics(**result.metrics),
            equity_curve=result.equity_curve,
            trade_log=result.trade_log,
            buy_hold_curve=result.buy_hold_curve,
            indicator_series=result.indicator_series or None,
            duration_ms=int(result.duration_ms),
        )
    except Exception as exc:
        logger.error("backtest_error", bt_id=bt_id, error=str(exc))
        await update_backtest_result(
            session, bt_id, {}, [], [], 0, status="error", error_message=str(exc)
        )
        raise HTTPException(status_code=500, detail=str(exc))


def _build_metrics(bt) -> BacktestMetrics:
    return BacktestMetrics(
        sharpe_ratio=bt.sharpe_ratio,
        sortino_ratio=bt.sortino_ratio,
        max_drawdown=bt.max_drawdown,
        win_rate=bt.win_rate,
        profit_factor=bt.profit_factor,
        total_return=bt.total_return,
        annualized_return=bt.annualized_return,
        num_trades=bt.num_trades,
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
