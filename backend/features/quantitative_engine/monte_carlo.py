"""Vectorized Monte Carlo simulator using Euler-Maruyama discretization of Vasicek+Jump SDE.

SDE: dS_t = k(theta - S_t)dt + sigma*dW_t + dJ_d(t) + dJ_u(t)
"""
import time
from dataclasses import dataclass

import numpy as np

from features.quantitative_engine.jump_diffusion import JumpParams, compound_poisson_process
from features.quantitative_engine.vasicek import VasicekParams
from utils.logging import get_logger

logger = get_logger(__name__)

PERCENTILES = [5, 25, 50, 75, 95]


@dataclass
class SimulationStats:
    mean_terminal: float
    std_terminal: float
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float
    prob_positive_return: float
    mean_max_drawdown: float


@dataclass
class SimulationResult:
    paths: np.ndarray          # shape: (steps+1, n_paths)
    stats: SimulationStats
    percentile_paths: dict     # key: percentile string, value: list of floats
    duration_ms: float


def simulate_paths(
    vasicek: VasicekParams,
    jump_params: JumpParams,
    s0: float,
    dt: float,
    steps: int,
    n_paths: int,
    seed: int | None = None,
) -> np.ndarray:
    """Core Euler-Maruyama simulation. Returns array of shape (steps+1, n_paths)."""
    if seed is not None:
        np.random.seed(seed)

    paths = np.empty((steps + 1, n_paths), dtype=np.float64)
    paths[0] = s0

    sqrt_dt = np.sqrt(dt)
    dW = np.random.normal(0.0, sqrt_dt, size=(steps, n_paths))

    for t in range(steps):
        s_t = paths[t]
        drift = vasicek.k * (vasicek.theta - s_t) * dt
        diffusion = vasicek.sigma * dW[t]
        j_up = compound_poisson_process(jump_params.lambda_up, jump_params.up, n_paths, dt, sign=1.0)
        j_down = compound_poisson_process(jump_params.lambda_down, jump_params.down, n_paths, dt, sign=-1.0)
        paths[t + 1] = s_t + drift + diffusion + j_up + j_down

    return paths


def compute_path_statistics(paths: np.ndarray, s0: float) -> SimulationStats:
    """Compute summary statistics over all Monte Carlo paths."""
    terminal = paths[-1]
    pct_values = np.percentile(terminal, PERCENTILES)
    returns = (terminal - s0) / s0
    prob_positive = float(np.mean(returns > 0))
    drawdowns = _compute_max_drawdowns(paths)
    mean_mdd = float(np.mean(drawdowns))

    return SimulationStats(
        mean_terminal=float(np.mean(terminal)),
        std_terminal=float(np.std(terminal)),
        p5=float(pct_values[0]),
        p25=float(pct_values[1]),
        p50=float(pct_values[2]),
        p75=float(pct_values[3]),
        p95=float(pct_values[4]),
        prob_positive_return=prob_positive,
        mean_max_drawdown=mean_mdd,
    )


def _compute_max_drawdowns(paths: np.ndarray) -> np.ndarray:
    """Compute max drawdown for each path. Returns array of shape (n_paths,)."""
    cummax = np.maximum.accumulate(paths, axis=0)
    drawdowns = (paths - cummax) / np.where(cummax > 0, cummax, 1.0)
    return np.min(drawdowns, axis=0)


def extract_percentile_paths(paths: np.ndarray) -> dict:
    """Extract representative paths at each percentile for frontend charting."""
    terminal = paths[-1]
    result = {}
    for pct in PERCENTILES:
        thresh = np.percentile(terminal, pct)
        idx = int(np.argmin(np.abs(terminal - thresh)))
        result[str(pct)] = paths[:, idx].tolist()
    return result


def run_simulation(
    vasicek: VasicekParams,
    jump_params: JumpParams,
    s0: float,
    dt: float,
    steps: int,
    n_paths: int,
    seed: int | None = None,
) -> SimulationResult:
    """Full simulation pipeline: simulate → statistics → percentile paths."""
    t0 = time.perf_counter()
    paths = simulate_paths(vasicek, jump_params, s0, dt, steps, n_paths, seed=seed)
    stats = compute_path_statistics(paths, s0)
    pct_paths = extract_percentile_paths(paths)
    duration_ms = (time.perf_counter() - t0) * 1000

    logger.info(
        "simulation_complete",
        n_paths=n_paths,
        steps=steps,
        duration_ms=round(duration_ms, 2),
        p50=round(stats.p50, 4),
    )
    return SimulationResult(paths=paths, stats=stats, percentile_paths=pct_paths, duration_ms=duration_ms)
