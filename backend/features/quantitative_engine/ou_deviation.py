"""Ornstein-Uhlenbeck model on log price deviation from rolling mean."""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from features.quantitative_engine.jump_diffusion import JumpParams
from features.quantitative_engine.merton_jump_diffusion import _multiplicative_jump
from features.quantitative_engine.monte_carlo import (
    SimulationResult,
    compute_path_statistics,
    extract_percentile_paths,
)
from utils.logging import get_logger

logger = get_logger(__name__)

MIN_OBSERVATIONS = 30


@dataclass
class OuDeviationParams:
    kappa: float
    theta: float
    sigma: float
    ma_window: int
    ma_level: float
    x0: float
    r_squared: float = 0.0


def _rolling_ma(prices: np.ndarray, window: int) -> np.ndarray:
    series = pd.Series(prices, dtype=float)
    return series.rolling(window, min_periods=window).mean().to_numpy(dtype=float)


def _deviation_series(prices: np.ndarray, ma_window: int) -> tuple[np.ndarray, np.ndarray]:
    ma = _rolling_ma(prices, ma_window)
    valid = np.isfinite(ma) & (ma > 0) & (prices > 0)
    x = np.full(len(prices), np.nan, dtype=float)
    x[valid] = np.log(prices[valid] / ma[valid])
    return x, ma


def estimate_ou_deviation_params(
    prices: np.ndarray,
    ma_window: int,
    dt: float,
) -> OuDeviationParams:
    """Estimate OU parameters on log(S/MA) via OLS: dX = kappa*(theta - X)*dt + noise."""
    prices = np.asarray(prices, dtype=float)
    x_series, ma = _deviation_series(prices, ma_window)
    valid = np.isfinite(x_series)
    x = x_series[valid]
    if len(x) < MIN_OBSERVATIONS:
        raise ValueError(f"Need at least {MIN_OBSERVATIONS} deviation obs, got {len(x)}")

    dx = np.diff(x)
    x_t = x[:-1]
    slope, intercept, r_value, _, _ = stats.linregress(x_t, dx)
    kappa = max(-slope / dt, 1e-6)
    theta = intercept / (kappa * dt) if kappa > 1e-6 else float(np.mean(x))
    residuals = dx - (intercept + slope * x_t)
    sigma = float(np.std(residuals) / np.sqrt(dt))

    last_ma = float(ma[np.where(np.isfinite(ma))[0][-1]])
    x0 = float(x[-1])
    logger.info(
        "ou_deviation_params_estimated",
        kappa=round(kappa, 6),
        theta=round(theta, 6),
        sigma=round(sigma, 6),
        ma_window=ma_window,
    )
    return OuDeviationParams(
        kappa=kappa,
        theta=theta,
        sigma=sigma,
        ma_window=ma_window,
        ma_level=last_ma,
        x0=x0,
        r_squared=float(r_value ** 2),
    )


def _apply_price_jumps(
    s_t: np.ndarray,
    jump_params: JumpParams,
    n_paths: int,
    dt: float,
) -> np.ndarray:
    j_up = _multiplicative_jump(
        jump_params.lambda_up, jump_params.up, s_t, n_paths, dt, sign=1.0,
    )
    j_down = _multiplicative_jump(
        jump_params.lambda_down, jump_params.down, s_t, n_paths, dt, sign=-1.0,
    )
    return j_up + j_down


def simulate_ou_deviation_paths(
    params: OuDeviationParams,
    jump_params: JumpParams,
    s0: float,
    dt: float,
    steps: int,
    n_paths: int,
    seed: int | None = None,
) -> np.ndarray:
    """Simulate price paths via OU on log-deviation; MA held fixed over horizon."""
    if seed is not None:
        np.random.seed(seed)

    ma_level = params.ma_level if params.ma_level > 0 else s0
    x0 = params.x0 if np.isfinite(params.x0) else float(np.log(s0 / ma_level))
    paths = np.empty((steps + 1, n_paths), dtype=np.float64)
    paths[0] = s0

    x_paths = np.full((steps + 1, n_paths), x0, dtype=np.float64)
    sqrt_dt = np.sqrt(dt)
    dW = np.random.normal(0.0, sqrt_dt, size=(steps, n_paths))

    for t in range(steps):
        x_t = x_paths[t]
        drift_x = params.kappa * (params.theta - x_t) * dt
        diffusion_x = params.sigma * dW[t]
        x_next = x_t + drift_x + diffusion_x
        s_base = ma_level * np.exp(x_next)
        price_jumps = _apply_price_jumps(s_base, jump_params, n_paths, dt)
        paths[t + 1] = np.maximum(s_base + price_jumps, 0.0)
        x_paths[t + 1] = np.log(np.maximum(paths[t + 1], 1e-12) / ma_level)

    return paths


def run_ou_deviation_simulation(
    params: OuDeviationParams,
    jump_params: JumpParams,
    s0: float,
    dt: float,
    steps: int,
    n_paths: int,
    seed: int | None = None,
) -> SimulationResult:
    """Full OU-deviation simulation pipeline."""
    t0 = time.perf_counter()
    paths = simulate_ou_deviation_paths(
        params, jump_params, s0, dt, steps, n_paths, seed=seed,
    )
    stats = compute_path_statistics(paths, s0)
    pct_paths = extract_percentile_paths(paths)
    duration_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "ou_deviation_simulation_complete",
        n_paths=n_paths,
        steps=steps,
        duration_ms=round(duration_ms, 2),
        p50=round(stats.p50, 4),
    )
    return SimulationResult(
        paths=paths, stats=stats, percentile_paths=pct_paths, duration_ms=duration_ms,
    )


def run_single_step_ou_prob(
    params: OuDeviationParams,
    jump_params: JumpParams,
    s0: float,
    dt: float,
    n_paths: int,
    seed: int | None = None,
) -> float:
    """Run 1-step OU-deviation MC and return prob_positive_return."""
    sim_params = OuDeviationParams(
        kappa=params.kappa,
        theta=params.theta,
        sigma=params.sigma,
        ma_window=params.ma_window,
        ma_level=params.ma_level,
        x0=float(np.log(s0 / params.ma_level)) if params.ma_level > 0 else params.x0,
    )
    result = run_ou_deviation_simulation(
        sim_params, jump_params, s0, dt, steps=1, n_paths=n_paths, seed=seed,
    )
    return result.stats.prob_positive_return
