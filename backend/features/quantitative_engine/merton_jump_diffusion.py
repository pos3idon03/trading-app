"""Merton Jump-Diffusion model simulation.

SDE (Euler-Maruyama, multiplicative form):
    dS_t = μ S_t dt + σ S_t dW_t + S_t dJ^up_t + S_t dJ^down_t

where:
    μ     = annualized drift (mean log-return / dt)
    σ     = annualized volatility (std log-return / sqrt(dt))
    dW_t  ~ N(0, dt)
    dJ^up / dJ^down = compound Poisson jumps scaled by S_t

Discrete step:
    S_{t+1} = S_t + μ S_t dt + σ S_t dW_t + S_t (j_up + j_down)

Jumps are multiplicative: a lognormal jump of size y causes ±y*S_t change,
so the same jump % applies regardless of price level.
"""
import time
from dataclasses import dataclass

import numpy as np

from features.quantitative_engine.jump_diffusion import JumpParams, compound_poisson_process
from features.quantitative_engine.monte_carlo import (
    SimulationResult,
    SimulationStats,
    compute_path_statistics,
    extract_percentile_paths,
)
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MertonParams:
    mu: float     # annualized drift rate (mean log-return / dt)
    sigma: float  # annualized volatility (std log-return / sqrt(dt))


def simulate_merton_paths(
    params: MertonParams,
    jump_params: JumpParams,
    s0: float,
    dt: float,
    steps: int,
    n_paths: int,
    seed: int | None = None,
) -> np.ndarray:
    """Euler-Maruyama simulation of Merton Jump-Diffusion.

    Returns array of shape (steps+1, n_paths). All increments are
    proportional to the current price level (multiplicative), so paths
    naturally compound upward and cannot cross zero in the diffusion term.
    """
    if seed is not None:
        np.random.seed(seed)

    paths = np.empty((steps + 1, n_paths), dtype=np.float64)
    paths[0] = s0

    sqrt_dt = np.sqrt(dt)
    dW = np.random.normal(0.0, sqrt_dt, size=(steps, n_paths))

    for t in range(steps):
        s_t = paths[t]
        drift = params.mu * s_t * dt
        diffusion = params.sigma * s_t * dW[t]
        j_up = _multiplicative_jump(jump_params.lambda_up, jump_params.up, s_t, n_paths, dt, sign=1.0)
        j_down = _multiplicative_jump(jump_params.lambda_down, jump_params.down, s_t, n_paths, dt, sign=-1.0)
        paths[t + 1] = np.maximum(s_t + drift + diffusion + j_up + j_down, 0.0)

    return paths


def _multiplicative_jump(
    lambda_: float,
    dist_params,
    s_t: np.ndarray,
    n_paths: int,
    dt: float,
    sign: float,
) -> np.ndarray:
    """Sample one time step of a multiplicative compound Poisson jump.

    Jump increment = sign * S_t * sum(lognormal_sizes), so the jump is
    proportional to the current price level.
    """
    jump_counts = np.random.poisson(lambda_ * dt, size=n_paths)
    increments = np.zeros(n_paths)

    active = np.where(jump_counts > 0)[0]
    if len(active) == 0:
        return increments

    for i in active:
        n_jumps = jump_counts[i]
        sizes = np.random.lognormal(mean=dist_params.mu, sigma=dist_params.sigma, size=n_jumps)
        increments[i] = sign * s_t[i] * np.sum(sizes)

    return increments


def run_merton_simulation(
    params: MertonParams,
    jump_params: JumpParams,
    s0: float,
    dt: float,
    steps: int,
    n_paths: int,
    seed: int | None = None,
) -> SimulationResult:
    """Full simulation pipeline for Merton model: simulate → statistics → percentile paths."""
    t0 = time.perf_counter()
    paths = simulate_merton_paths(params, jump_params, s0, dt, steps, n_paths, seed=seed)
    stats = compute_path_statistics(paths, s0)
    pct_paths = extract_percentile_paths(paths)
    duration_ms = (time.perf_counter() - t0) * 1000

    logger.info(
        "merton_simulation_complete",
        n_paths=n_paths,
        steps=steps,
        duration_ms=round(duration_ms, 2),
        p50=round(stats.p50, 4),
    )
    return SimulationResult(paths=paths, stats=stats, percentile_paths=pct_paths, duration_ms=duration_ms)
