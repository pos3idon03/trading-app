"""Backtesting API routes."""
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_asset_id_by_symbol, get_ohlcv
from dal.simulation_dal import get_simulation
from db import get_db
from dtos.backtest_dto import (
    VALID_STRATEGIES,
    BacktestMetrics,
    BacktestRequest,
    BacktestResponse,
    ChartOverlayRequest,
    ChartOverlayResponse,
    ComboBacktestRequest,
    ComboSignalsResponse,
    ComboStrategySignal,
    OptimizationRequest,
    OptimizationResponse,
    OptimizationSummary,
    SignalPoint,
)
from features.backtesting.chart_overlay import (
    compute_chart_overlay,
    load_ohlcv_for_overlay,
    resolve_asset_id,
)
from features.backtesting.combo_runner import (
    ComboStrategyConfig,
    run_combo_backtest,
    run_per_strategy_backtests,
)
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
    simulated paths (via simulation_id). Results are computed on the fly and
    not stored in the database.
    """
    if request.simulation_id is not None:
        return await _run_simulated_backtest(session, request)
    return await _run_historical_backtest(session, request)


@router.get("/catalog", response_model=list[str])
async def get_strategy_catalog() -> list[str]:
    """Return sorted list of supported backtest strategy names."""
    return sorted(VALID_STRATEGIES)


@router.post("/chart-overlay", response_model=ChartOverlayResponse, status_code=200)
async def compute_overlay(
    request: ChartOverlayRequest,
    session: AsyncSession = Depends(get_db),
) -> ChartOverlayResponse:
    """Run a strategy in-memory over the OHLCV slice and return indicator/trade data.

    No data is written to the database. Intended for chart visualisation only.
    """
    asset_id = await resolve_asset_id(session, request.asset_id, request.symbol)
    if asset_id is None:
        raise HTTPException(status_code=404, detail=f"Asset '{request.symbol}' not found")

    df = await load_ohlcv_for_overlay(
        session,
        asset_id=asset_id,
        timeframe=request.timeframe,
        start=request.start_date,
        end=request.end_date,
    )

    if df.empty:
        symbol_label = request.symbol or str(request.asset_id)
        raise HTTPException(
            status_code=404,
            detail=(
                f"No {request.timeframe} price data available for {symbol_label}. "
                "Load chart data first or select a different timeframe."
            ),
        )
    if len(df) < 20:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient data for strategy overlay: {len(df)} bars (need ≥ 20)",
        )

    try:
        payload = compute_chart_overlay(
            df,
            strategy_name=request.strategy_name,
            strategy_params=request.strategy_params,
            timeframe=request.timeframe,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("chart_overlay_error", strategy=request.strategy_name, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return ChartOverlayResponse(**payload)


@router.post("/combo", response_model=BacktestResponse, status_code=202)
async def execute_combo_backtest(
    request: ComboBacktestRequest,
    session: AsyncSession = Depends(get_db),
) -> BacktestResponse:
    """Execute a combination backtest that merges signals from 2+ strategies.

    Supports AND (unanimous), majority voting, and weighted-threshold modes.
    Results are computed on the fly and not stored in the database.
    """
    if request.simulation_id is not None:
        return await _run_combo_simulated(session, request)
    return await _run_combo_historical(session, request)


@router.post("/combo-signals", response_model=ComboSignalsResponse, status_code=200)
async def execute_combo_signals(
    request: ComboBacktestRequest,
    session: AsyncSession = Depends(get_db),
) -> ComboSignalsResponse:
    """Return per-strategy backtest results and signal timelines for a combo.

    Runs each strategy leg independently over the same OHLCV window so the UI
    can display individual equity curves, buy/sell markers and the unified
    Buy/Sell signal timeline chart.
    """
    asset_id = await _resolve_asset_id(session, request.asset_id, request.symbol)
    df = await get_ohlcv(
        session,
        asset_id=asset_id,
        start=request.start_date,
        end=request.end_date,
        **_ohlcv_query_args(request.timeframe),
    )

    if df.empty:
        symbol_label = request.symbol or str(request.asset_id)
        raise HTTPException(
            status_code=404,
            detail=(
                f"No {request.timeframe} price data for {symbol_label}. "
                "Ingest data for this frequency first."
            ),
        )
    if len(df) < 20:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient data for combo signals: {len(df)} rows",
        )

    return _compute_combo_signals(request, df)


def _compute_combo_signals(
    request: ComboBacktestRequest,
    df,
) -> ComboSignalsResponse:
    configs = [
        ComboStrategyConfig(
            strategy_name=s.strategy_name,
            strategy_params=s.strategy_params,
            weight=s.weight,
        )
        for s in request.strategies
    ]
    try:
        per_strategy = run_per_strategy_backtests(
            df,
            strategies=configs,
            timeframe=request.timeframe,
            initial_capital=request.initial_capital,
        )
        strategies = [
            ComboStrategySignal(
                strategy_name=r.strategy_name,
                trade_log=r.trade_log,
                indicator_series=r.indicator_series,
                equity_curve=r.equity_curve,
                signal_timeline=[
                    SignalPoint(time=p["time"], signal=p["signal"])
                    for p in r.signal_timeline
                ],
            )
            for r in per_strategy
        ]
        return ComboSignalsResponse(strategies=strategies)
    except Exception as exc:
        logger.error("combo_signals_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/optimize", response_model=OptimizationResponse, status_code=202)
async def run_optimization(
    request: OptimizationRequest,
    session: AsyncSession = Depends(get_db),
) -> OptimizationResponse:
    """Walk-forward parameter optimization for a strategy over historical data.

    Results are computed on the fly and not stored in the database.
    """
    asset_id = await _resolve_asset_id(session, request.asset_id, request.symbol)

    df = await get_ohlcv(
        session,
        asset_id=asset_id,
        start=request.start_date,
        end=request.end_date,
        **_ohlcv_query_args(request.timeframe),
    )

    if df.empty:
        symbol_label = request.symbol or str(request.asset_id)
        raise HTTPException(
            status_code=404,
            detail=(
                f"No {request.timeframe} price data available for {symbol_label}. "
                "Ingest data for this frequency first or select a different Price Frequency."
            ),
        )
    min_rows = (request.n_splits + 1) * 30
    if len(df) < min_rows:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient data for walk-forward optimization: {len(df)} rows (need {min_rows})",
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

        return OptimizationResponse(
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
        logger.error("optimization_error", strategy=request.strategy_name, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ohlcv_query_args(timeframe: str) -> dict:
    """Return get_ohlcv keyword args for the given timeframe."""
    _RESAMPLE_FROM_5M: dict[str, timedelta] = {
        "15m": timedelta(minutes=15),
        "30m": timedelta(minutes=30),
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
    }
    if timeframe == "1w":
        return {"timeframe": "1d", "bucket_interval": timedelta(weeks=1)}
    if timeframe in _RESAMPLE_FROM_5M:
        return {"timeframe": "5m", "bucket_interval": _RESAMPLE_FROM_5M[timeframe]}
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

    if df.empty:
        symbol_label = request.symbol or str(request.asset_id)
        raise HTTPException(
            status_code=404,
            detail=(
                f"No {request.timeframe} price data available for {symbol_label}. "
                "Ingest data for this frequency first or select a different Price Frequency."
            ),
        )
    if len(df) < 20:
        raise HTTPException(status_code=422, detail=f"Insufficient data for backtest: {len(df)} rows")

    return _compute_backtest(request, df, asset_id)


async def _run_simulated_backtest(
    session: AsyncSession,
    request: BacktestRequest,
) -> BacktestResponse:
    sim = await get_simulation(session, request.simulation_id)
    if sim is None:
        raise HTTPException(status_code=404, detail=f"Simulation {request.simulation_id} not found")
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
        raise HTTPException(status_code=422, detail=f"Simulated path too short for backtest: {len(df)} rows")

    return _compute_backtest(request, df, sim.asset_id)


def _compute_backtest(request: BacktestRequest, df, asset_id: int) -> BacktestResponse:
    try:
        result = run_backtest(
            df,
            strategy=request.strategy_name,
            params=request.strategy_params,
            initial_capital=request.initial_capital,
            timeframe=request.timeframe,
        )
        return BacktestResponse(
            asset_id=asset_id,
            strategy_name=request.strategy_name,
            strategy_params=request.strategy_params or {},
            status="done",
            metrics=BacktestMetrics(**result.metrics),
            equity_curve=result.equity_curve,
            trade_log=result.trade_log,
            buy_hold_curve=result.buy_hold_curve,
            indicator_series=result.indicator_series or None,
            duration_ms=int(result.duration_ms),
        )
    except Exception as exc:
        logger.error("backtest_error", strategy=request.strategy_name, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


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

    if df.empty:
        symbol_label = request.symbol or str(request.asset_id)
        raise HTTPException(
            status_code=404,
            detail=(
                f"No {request.timeframe} price data available for {symbol_label}. "
                "Ingest data for this frequency first or select a different Price Frequency."
            ),
        )
    if len(df) < 20:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient data for combo backtest: {len(df)} rows",
        )

    return _compute_combo(request, df, asset_id)


async def _run_combo_simulated(
    session: AsyncSession,
    request: ComboBacktestRequest,
) -> BacktestResponse:
    sim = await get_simulation(session, request.simulation_id)
    if sim is None:
        raise HTTPException(status_code=404, detail=f"Simulation {request.simulation_id} not found")
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

    return _compute_combo(request, df, sim.asset_id)


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


def _compute_combo(request: ComboBacktestRequest, df, asset_id: int) -> BacktestResponse:
    strategy_name = _build_combo_strategy_name(request)
    params = _build_combo_params(request)

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

        return BacktestResponse(
            asset_id=asset_id,
            strategy_name=strategy_name,
            strategy_params=params,
            status="done",
            metrics=BacktestMetrics(**result.metrics),
            equity_curve=result.equity_curve,
            trade_log=result.trade_log,
            buy_hold_curve=result.buy_hold_curve,
            duration_ms=int(result.duration_ms),
            monthly_breakdown=monthly_breakdown,
        )
    except Exception as exc:
        logger.error("combo_backtest_error", strategy=strategy_name, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


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
