"""Monte Carlo simulation API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_asset_id_by_symbol
from dal.simulation_dal import create_simulation, get_simulation, update_simulation_result
from db import get_db
from dtos.simulation_dto import (
    CalibrationRequest,
    CalibrationResponse,
    DistributionPoint,
    ReturnDistribution,
    SimulationRequest,
    SimulationResponse,
    SimulationStats,
)
from features.quantitative_engine.calibration_service import calibrate_model_for_asset
from features.quantitative_engine.merton_jump_diffusion import MertonParams as MertonInternal, run_merton_simulation
from features.quantitative_engine.monte_carlo import compute_return_distribution, run_simulation
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
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    elif request.custom_params:
        calibrated = request.custom_params
    else:
        raise HTTPException(status_code=400, detail="Provide custom_params or set use_stored_params=true")

    dt = _timeframe_to_dt(request.timeframe)
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
        jumps = _to_internal_jumps(calibrated.jumps)

        if request.model_type == "merton":
            if calibrated.merton is None:
                raise HTTPException(status_code=422, detail="Merton params not available; re-run calibration")
            merton = _to_internal_merton(calibrated.merton)
            result = run_merton_simulation(merton, jumps, s0, dt, request.horizon_steps, request.num_paths)
        else:
            vasicek = _to_internal_vasicek(calibrated.vasicek)
            result = run_simulation(vasicek, jumps, s0, dt, request.horizon_steps, request.num_paths)

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


def _to_internal_merton(dto) -> MertonInternal:
    return MertonInternal(mu=dto.mu, sigma=dto.sigma)


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


def _timeframe_to_dt(timeframe: str) -> float:
    mapping = {"1m": 1/252/390, "5m": 5/252/390, "15m": 15/252/390,
               "30m": 30/252/390, "1h": 1/252/6.5, "4h": 4/252/6.5,
               "1d": 1/252, "1w": 1/52}
    return mapping.get(timeframe, 1/252)


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
