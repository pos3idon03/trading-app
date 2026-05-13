"""Vasicek model parameter estimation via OLS on discretized SDE."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from utils.logging import get_logger

logger = get_logger(__name__)

MIN_OBSERVATIONS = 30


@dataclass
class VasicekParams:
    k: float            # mean reversion speed
    theta: float        # long-term mean (θ_0 in dynamic mode)
    sigma: float        # diffusion coefficient
    mu: float = 0.0     # expected drift rate: θ_t = θ_0 * exp(μ * t); 0 = static theta
    r_squared: float = 0.0


def estimate_drift_rate(prices: np.ndarray, dt: float) -> float:
    """Estimate the annualized log-return drift rate mu from historical prices.

    mu is the expected continuous growth rate (per year-fraction) used as the
    dynamic theta trend: θ_t = θ_0 * exp(μ * t). Computed as the mean log-return
    divided by the time step dt to annualise it.
    """
    prices = np.asarray(prices, dtype=float)
    prices = prices[prices > 0]
    if len(prices) < 2:
        return 0.0
    log_returns = np.diff(np.log(prices))
    return float(np.mean(log_returns) / dt)


def estimate_mean_reversion_params(prices: np.ndarray, dt: float = 1.0) -> VasicekParams:
    """Estimate Vasicek SDE parameters via OLS regression.

    Discretized form: S(t+1) - S(t) = k*(theta - S(t))*dt + epsilon
    Rearranged as OLS: dS = alpha + beta*S(t)
    Where: beta = -k*dt, alpha = k*theta*dt
    """
    if len(prices) < MIN_OBSERVATIONS:
        raise ValueError(f"Need at least {MIN_OBSERVATIONS} observations, got {len(prices)}")

    s = np.asarray(prices, dtype=float)
    ds = np.diff(s)
    s_t = s[:-1]

    slope, intercept, r_value, p_value, _ = stats.linregress(s_t, ds)

    k = max(-slope / dt, 1e-6)
    theta = intercept / (k * dt) if k > 1e-6 else float(s.mean())

    residuals = ds - (intercept + slope * s_t)
    sigma = float(np.std(residuals) / np.sqrt(dt))
    mu = estimate_drift_rate(s, dt)

    logger.info(
        "vasicek_params_estimated",
        k=round(k, 6),
        theta=round(theta, 4),
        sigma=round(sigma, 6),
        mu=round(mu, 6),
    )
    return VasicekParams(k=k, theta=theta, sigma=sigma, mu=mu, r_squared=r_value ** 2)


def _compute_log_returns(prices: np.ndarray) -> np.ndarray:
    prices = np.asarray(prices, dtype=float)
    prices = prices[prices > 0]
    return np.diff(np.log(prices))


def compute_historical_volatility(prices: np.ndarray, annualize: bool = True, trading_days: int = 252) -> float:
    """Annualized historical volatility from log returns."""
    log_returns = _compute_log_returns(prices)
    vol = float(np.std(log_returns))
    if annualize:
        vol *= np.sqrt(trading_days)
    return vol


def calibrate_vasicek(
    prices: np.ndarray,
    dt: float = 1.0 / 252,
    log_prices: bool = False,
) -> VasicekParams:
    """Full calibration: optionally work in log-price space for positivity."""
    data = np.log(prices) if log_prices else np.asarray(prices, dtype=float)
    return estimate_mean_reversion_params(data, dt=dt)
