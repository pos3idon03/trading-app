"""DAL for simulations, backtest results, and optimization runs."""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.simulation import BacktestResult, OptimizationRun, Simulation
from utils.logging import get_logger

logger = get_logger(__name__)


async def create_simulation(
    session: AsyncSession,
    asset_id: int,
    timeframe: str,
    params: dict,
    num_paths: int,
    horizon_steps: int,
    dt: float,
    s0: float,
    calibration_start: Optional[datetime] = None,
    calibration_end: Optional[datetime] = None,
) -> int:
    sim = Simulation(
        asset_id=asset_id,
        timeframe=timeframe,
        params=params,
        num_paths=num_paths,
        horizon_steps=horizon_steps,
        dt=dt,
        s0=s0,
        calibration_start=calibration_start,
        calibration_end=calibration_end,
        status="running",
    )
    session.add(sim)
    await session.flush()
    return sim.id


async def update_simulation_result(
    session: AsyncSession,
    sim_id: int,
    result_summary: dict,
    percentile_paths: dict,
    duration_ms: int,
    status: str = "done",
    error_message: Optional[str] = None,
) -> None:
    result = await session.get(Simulation, sim_id)
    if result is None:
        raise ValueError(f"Simulation {sim_id} not found")
    result.result_summary = result_summary
    result.percentile_paths = percentile_paths
    result.duration_ms = duration_ms
    result.status = status
    result.error_message = error_message


async def get_simulation(session: AsyncSession, sim_id: int) -> Optional[Simulation]:
    return await session.get(Simulation, sim_id)


async def create_backtest(
    session: AsyncSession,
    asset_id: int,
    strategy_name: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
    params: dict,
) -> int:
    bt = BacktestResult(
        asset_id=asset_id,
        strategy_name=strategy_name,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        params=params,
        status="running",
    )
    session.add(bt)
    await session.flush()
    return bt.id


async def update_backtest_result(
    session: AsyncSession,
    bt_id: int,
    metrics: dict,
    equity_curve: list,
    trade_log: list,
    duration_ms: int,
    buy_hold_curve: Optional[list] = None,
    status: str = "done",
    error_message: Optional[str] = None,
) -> None:
    bt = await session.get(BacktestResult, bt_id)
    if bt is None:
        raise ValueError(f"Backtest {bt_id} not found")
    for key, value in metrics.items():
        if hasattr(bt, key):
            setattr(bt, key, value)
    bt.equity_curve = equity_curve
    bt.trade_log = trade_log
    bt.buy_hold_curve = buy_hold_curve
    bt.duration_ms = duration_ms
    bt.status = status
    bt.error_message = error_message


async def get_backtest(session: AsyncSession, bt_id: int) -> Optional[BacktestResult]:
    return await session.get(BacktestResult, bt_id)


async def create_optimization(
    session: AsyncSession,
    asset_id: int,
    strategy_name: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
    param_grid: dict,
    n_splits: int,
    optimize_metric: str,
) -> int:
    run = OptimizationRun(
        asset_id=asset_id,
        strategy_name=strategy_name,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        param_grid=param_grid,
        n_splits=n_splits,
        optimize_metric=optimize_metric,
        status="running",
    )
    session.add(run)
    await session.flush()
    return run.id


async def update_optimization_result(
    session: AsyncSession,
    opt_id: int,
    best_params: dict,
    best_metric: float,
    all_results: list[dict],
    duration_ms: int,
    status: str = "done",
    error_message: Optional[str] = None,
) -> None:
    run = await session.get(OptimizationRun, opt_id)
    if run is None:
        raise ValueError(f"OptimizationRun {opt_id} not found")
    run.best_params = best_params
    run.best_metric = best_metric
    run.all_results = all_results
    run.duration_ms = duration_ms
    run.status = status
    run.error_message = error_message


async def get_optimization(session: AsyncSession, opt_id: int) -> Optional[OptimizationRun]:
    return await session.get(OptimizationRun, opt_id)
