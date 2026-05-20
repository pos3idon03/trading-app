"""ADX-weighted blend of Merton trend and OU deviation reversion probabilities."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from dtos.simulation_dto import CalibratedModelParams, OuDeviationParams as OuDeviationDto
from features.quantitative_engine.merton_jump_diffusion import MertonParams, run_merton_simulation
from features.quantitative_engine.monte_carlo import SimulationResult, SimulationStats
from features.quantitative_engine.ou_deviation import OuDeviationParams, run_ou_deviation_simulation
from features.quantitative_engine.regime_weight import trend_weight_from_adx


@dataclass
class BlendedProbResult:
    prob_effective: float
    prob_trend: float
    prob_reversion: float
    regime_weight: float


def _to_ou_internal(dto: OuDeviationDto, s0: float) -> OuDeviationParams:
    ma = dto.ma_level if dto.ma_level > 0 else s0
    x0 = float(np.log(s0 / ma)) if ma > 0 else dto.x0
    return OuDeviationParams(
        kappa=dto.kappa,
        theta=dto.theta,
        sigma=dto.sigma,
        ma_window=dto.ma_window,
        ma_level=ma,
        x0=x0,
    )


def _to_merton_internal(dto) -> MertonParams:
    return MertonParams(mu=dto.mu, sigma=dto.sigma)


def _to_jumps_internal(dto):
    from features.quantitative_engine.jump_diffusion import JumpDistParams, JumpParams

    return JumpParams(
        lambda_up=dto.lambda_up,
        lambda_down=dto.lambda_down,
        up=JumpDistParams(mu=dto.mu_up, sigma=dto.sigma_up),
        down=JumpDistParams(mu=dto.mu_down, sigma=dto.sigma_down),
    )


def _blend_stats(
    merton_stats: SimulationStats,
    ou_stats: SimulationStats,
    w_trend: float,
) -> SimulationStats:
    w_rev = 1.0 - w_trend
    return SimulationStats(
        mean_terminal=w_trend * merton_stats.mean_terminal + w_rev * ou_stats.mean_terminal,
        std_terminal=w_trend * merton_stats.std_terminal + w_rev * ou_stats.std_terminal,
        p5=w_trend * merton_stats.p5 + w_rev * ou_stats.p5,
        p25=w_trend * merton_stats.p25 + w_rev * ou_stats.p25,
        p50=w_trend * merton_stats.p50 + w_rev * ou_stats.p50,
        p75=w_trend * merton_stats.p75 + w_rev * ou_stats.p75,
        p95=w_trend * merton_stats.p95 + w_rev * ou_stats.p95,
        prob_positive_return=(
            w_trend * merton_stats.prob_positive_return
            + w_rev * ou_stats.prob_positive_return
        ),
        mean_max_drawdown=(
            w_trend * merton_stats.mean_max_drawdown
            + w_rev * ou_stats.mean_max_drawdown
        ),
    )


def run_blended_step_prob(
    params: CalibratedModelParams,
    s0: float,
    dt: float,
    n_paths: int,
    adx: float,
    adx_low: float = 15.0,
    adx_high: float = 25.0,
    seed: int | None = None,
    w_trend_override: float | None = None,
) -> BlendedProbResult:
    """1-step blended prob from Merton + OU with ADX or ML regime weight."""
    if params.merton is None or params.ou_deviation is None:
        raise ValueError("Blended model requires merton and ou_deviation params")

    jumps = _to_jumps_internal(params.jumps)
    if w_trend_override is not None:
        w_trend = float(np.clip(w_trend_override, 0.0, 1.0))
    else:
        w_trend = trend_weight_from_adx(adx, low=adx_low, high=adx_high)

    merton_result = run_merton_simulation(
        _to_merton_internal(params.merton), jumps, s0, dt, steps=1, n_paths=n_paths, seed=seed,
    )
    ou_result = run_ou_deviation_simulation(
        _to_ou_internal(params.ou_deviation, s0), jumps, s0, dt, steps=1, n_paths=n_paths, seed=seed,
    )
    p_trend = merton_result.stats.prob_positive_return
    p_rev = ou_result.stats.prob_positive_return
    p_eff = w_trend * p_trend + (1.0 - w_trend) * p_rev
    return BlendedProbResult(
        prob_effective=p_eff,
        prob_trend=p_trend,
        prob_reversion=p_rev,
        regime_weight=w_trend,
    )


def run_blended_simulation(
    params: CalibratedModelParams,
    s0: float,
    dt: float,
    steps: int,
    n_paths: int,
    adx: float,
    adx_low: float = 15.0,
    adx_high: float = 25.0,
    seed: int | None = None,
) -> SimulationResult:
    """Multi-step blended simulation; percentile paths from Merton, stats blended."""
    if params.merton is None or params.ou_deviation is None:
        raise ValueError("Blended model requires merton and ou_deviation params")

    jumps = _to_jumps_internal(params.jumps)
    w_trend = trend_weight_from_adx(adx, low=adx_low, high=adx_high)

    merton_result = run_merton_simulation(
        _to_merton_internal(params.merton), jumps, s0, dt, steps, n_paths, seed=seed,
    )
    ou_result = run_ou_deviation_simulation(
        _to_ou_internal(params.ou_deviation, s0), jumps, s0, dt, steps, n_paths, seed=seed,
    )
    blended_stats = _blend_stats(merton_result.stats, ou_result.stats, w_trend)
    return SimulationResult(
        paths=merton_result.paths,
        stats=blended_stats,
        percentile_paths=merton_result.percentile_paths,
        duration_ms=merton_result.duration_ms + ou_result.duration_ms,
    )
