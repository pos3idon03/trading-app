"""Monte Carlo (Merton Jump-Diffusion) runner for Strategy Builder cards.

Fixed parameters per spec:
  - model_type : merton
  - num_paths  : 10 000
  - horizon    : 126 trading days (~6 months)
  - calibration: 5 years of daily data
"""
from datetime import timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_asset_id_by_symbol
from dal.simulation_dal import create_simulation, get_simulation, update_simulation_result
from dtos.strategy_builder_dto import MonteCarloSummary
from features.quantitative_engine.calibration_service import calibrate_model_for_asset
from features.quantitative_engine.jump_diffusion import JumpDistParams
from features.quantitative_engine.jump_diffusion import JumpParams as JumpInternal
from features.quantitative_engine.merton_jump_diffusion import MertonParams as MertonInternal
from features.quantitative_engine.merton_jump_diffusion import run_merton_simulation
from utils.logging import get_logger
from utils.time_utils import utcnow

logger = get_logger(__name__)

_NUM_PATHS = 10_000
_HORIZON_STEPS = 126
_CALIBRATION_YEARS = 5
_DT = 1 / 252  # daily


async def get_or_run_merton_for_asset(
    session: AsyncSession,
    asset_id: int,
    cached_sim_id: Optional[int] = None,
) -> MonteCarloSummary:
    """Return a Monte Carlo summary, re-using a cached simulation if it is fresh."""
    if cached_sim_id is not None:
        summary = await _load_cached_simulation(session, cached_sim_id)
        if summary is not None:
            return summary

    return await _run_new_merton_simulation(session, asset_id)


async def _load_cached_simulation(
    session: AsyncSession,
    sim_id: int,
) -> Optional[MonteCarloSummary]:
    sim = await get_simulation(session, sim_id)
    if sim is None or sim.status != "done" or sim.result_summary is None:
        return None

    age = utcnow() - sim.created_at.replace(tzinfo=sim.created_at.tzinfo or None)
    if age > timedelta(days=1):
        return None

    return _build_summary(sim.id, sim.result_summary, cached=True)


async def _run_new_merton_simulation(
    session: AsyncSession,
    asset_id: int,
) -> MonteCarloSummary:
    calibrated = await calibrate_model_for_asset(
        session,
        asset_id=asset_id,
        timeframe="1d",
        calibration_years=_CALIBRATION_YEARS,
    )

    if calibrated.merton is None:
        raise ValueError("Merton params not available after calibration")

    merton = MertonInternal(mu=calibrated.merton.mu, sigma=calibrated.merton.sigma)
    jumps = _to_internal_jumps(calibrated.jumps)
    s0 = calibrated.last_price
    params_dict = calibrated.model_dump(mode="json")

    sim_id = await create_simulation(
        session,
        asset_id=asset_id,
        timeframe="1d",
        params=params_dict,
        num_paths=_NUM_PATHS,
        horizon_steps=_HORIZON_STEPS,
        dt=_DT,
        s0=s0,
        calibration_start=calibrated.calibration_start,
        calibration_end=calibrated.calibration_end,
    )

    result = run_merton_simulation(merton, jumps, s0, _DT, _HORIZON_STEPS, _NUM_PATHS)
    summary_dict = _stats_to_dict(result.stats)

    await update_simulation_result(
        session,
        sim_id=sim_id,
        result_summary=summary_dict,
        percentile_paths=result.percentile_paths,
        duration_ms=int(result.duration_ms),
    )

    return _build_summary(sim_id, summary_dict, cached=False)


def _build_summary(sim_id: int, result_summary: dict, cached: bool) -> MonteCarloSummary:
    return MonteCarloSummary(
        simulation_id=sim_id,
        prob_positive_return=result_summary.get("prob_positive_return", 0.0),
        mean_max_drawdown=result_summary.get("mean_max_drawdown", 0.0),
        p5=result_summary.get("p5", 0.0),
        p25=result_summary.get("p25", 0.0),
        p50=result_summary.get("p50", 0.0),
        p75=result_summary.get("p75", 0.0),
        p95=result_summary.get("p95", 0.0),
        mean_terminal=result_summary.get("mean_terminal", 0.0),
        std_terminal=result_summary.get("std_terminal", 0.0),
        cached=cached,
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


def _to_internal_jumps(dto) -> JumpInternal:
    return JumpInternal(
        lambda_up=dto.lambda_up,
        lambda_down=dto.lambda_down,
        up=JumpDistParams(mu=dto.mu_up, sigma=dto.sigma_up),
        down=JumpDistParams(mu=dto.mu_down, sigma=dto.sigma_down),
    )
