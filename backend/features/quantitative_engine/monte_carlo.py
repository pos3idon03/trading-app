"""Vectorized Monte Carlo simulator using Euler-Maruyama discretization of Vasicek+Jump SDE.

SDE: dS_t = k(θ_t - S_t)dt + sigma*dW_t + dJ_d(t) + dJ_u(t)

Where the long-term mean target follows a deterministic trend:
    θ_t = θ_0 * exp(μ * t)

Setting μ=0 (default) recovers the classic static-theta Vasicek model.
"""
import time
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from scipy.stats import gaussian_kde, norm

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
class DistributionData:
    """Decomposed return distribution for charting."""
    histogram: List[Tuple[float, float]]       # (bin_midpoint, density)
    mr_density: List[Tuple[float, float]]      # mean-reverting (normal) component
    jump_up_density: List[Tuple[float, float]] # positive jump component
    jump_down_density: List[Tuple[float, float]]  # negative jump component


@dataclass
class SimulationResult:
    paths: np.ndarray          # shape: (steps+1, n_paths)
    stats: SimulationStats
    percentile_paths: dict     # key: percentile string, value: list of floats
    duration_ms: float


def _dynamic_theta(theta0: float, mu: float, t: int, dt: float) -> float:
    """Compute the dynamic mean reversion target: θ_t = θ_0 * exp(μ * t * dt)."""
    return theta0 * np.exp(mu * t * dt)


def simulate_paths(
    vasicek: VasicekParams,
    jump_params: JumpParams,
    s0: float,
    dt: float,
    steps: int,
    n_paths: int,
    seed: int | None = None,
) -> np.ndarray:
    """Core Euler-Maruyama simulation. Returns array of shape (steps+1, n_paths).

    The drift uses a time-varying mean reversion target θ_t = θ_0 * exp(μ * t * dt).
    When vasicek.mu == 0, θ_t = θ_0 (classic static Vasicek).
    """
    if seed is not None:
        np.random.seed(seed)

    paths = np.empty((steps + 1, n_paths), dtype=np.float64)
    paths[0] = s0

    sqrt_dt = np.sqrt(dt)
    dW = np.random.normal(0.0, sqrt_dt, size=(steps, n_paths))

    for t in range(steps):
        s_t = paths[t]
        theta_t = _dynamic_theta(vasicek.theta, vasicek.mu, t, dt)
        drift = vasicek.k * (theta_t - s_t) * dt
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


def _kde_points(data: np.ndarray, x_grid: np.ndarray) -> List[Tuple[float, float]]:
    """Evaluate a Gaussian KDE on x_grid. Returns [(x, density), ...]."""
    if len(data) < 2:
        return [(float(x), 0.0) for x in x_grid]
    kde = gaussian_kde(data)
    return [(float(x), float(y)) for x, y in zip(x_grid, kde(x_grid))]


def compute_return_distribution(
    paths: np.ndarray,
    vasicek: VasicekParams,
    jump_params: JumpParams,
    n_bins: int = 60,
) -> DistributionData:
    """Build decomposed log-return distribution from simulated paths.

    Returns histogram of MC log-returns plus three density curves:
    mean-reverting (normal) component, negative-jump component, positive-jump component.
    """
    # Flatten all step-to-step log-returns from every path
    positive_paths = np.where(paths > 0, paths, np.nan)
    log_returns = np.diff(np.log(positive_paths), axis=0).flatten()
    log_returns = log_returns[np.isfinite(log_returns)]

    counts, edges = np.histogram(log_returns, bins=n_bins, density=True)
    midpoints = 0.5 * (edges[:-1] + edges[1:])
    histogram = [(float(m), float(c)) for m, c in zip(midpoints, counts)]

    x_min, x_max = float(edges[0]), float(edges[-1])
    x_grid = np.linspace(x_min, x_max, 200)

    # Mean-reverting component: normal distribution centred on drift
    mr_sigma = vasicek.sigma
    mr_densities = [(float(x), float(norm.pdf(x, loc=0.0, scale=mr_sigma))) for x in x_grid]

    # Jump component densities via KDE on classified tails (|z| > 3 of log_returns)
    mu_lr = float(np.mean(log_returns))
    std_lr = float(np.std(log_returns))
    if std_lr > 0:
        z = (log_returns - mu_lr) / std_lr
        up_jumps = log_returns[z > 3.0]
        down_jumps = log_returns[z < -3.0]
    else:
        up_jumps = np.array([])
        down_jumps = np.array([])

    jump_up_density = _kde_points(up_jumps, x_grid)
    jump_down_density = _kde_points(down_jumps, x_grid)

    return DistributionData(
        histogram=histogram,
        mr_density=mr_densities,
        jump_up_density=jump_up_density,
        jump_down_density=jump_down_density,
    )


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
