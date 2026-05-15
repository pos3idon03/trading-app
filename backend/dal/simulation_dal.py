"""DAL for Monte Carlo simulations."""
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.simulation import Simulation
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
