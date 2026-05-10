"""Jump process detection and calibration for the Vasicek+Jump model."""
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import stats

from utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_JUMP_THRESHOLD_SIGMA = 3.0  # z-score threshold for jump detection


@dataclass
class JumpDistParams:
    mu: float    # mean jump size (log-normal scale)
    sigma: float # std dev of jump size


@dataclass
class JumpCI:
    """95% confidence intervals for a single jump component's log-normal parameters."""
    mu_low: float
    mu_high: float
    sigma_low: float
    sigma_high: float


@dataclass
class JumpParams:
    lambda_up: float       # Poisson rate for upward jumps (per time unit)
    lambda_down: float     # Poisson rate for downward jumps
    up: JumpDistParams
    down: JumpDistParams
    ci_up: Optional[JumpCI] = field(default=None)
    ci_down: Optional[JumpCI] = field(default=None)


@dataclass
class JumpEvents:
    up_jumps: np.ndarray
    down_jumps: np.ndarray
    threshold: float
    detection_sigma: float


def detect_jumps(returns: np.ndarray, threshold_sigma: float = DEFAULT_JUMP_THRESHOLD_SIGMA) -> JumpEvents:
    """Identify jump events from return series using z-score thresholding.

    A return is classified as a jump when |z| > threshold_sigma.
    """
    r = np.asarray(returns, dtype=float)
    mu = np.mean(r)
    sigma = np.std(r)
    z_scores = (r - mu) / sigma if sigma > 0 else np.zeros_like(r)

    threshold = threshold_sigma * sigma
    up_jumps = r[z_scores > threshold_sigma]
    down_jumps = r[z_scores < -threshold_sigma]

    logger.info(
        "jumps_detected",
        up_count=len(up_jumps),
        down_count=len(down_jumps),
        threshold=round(threshold, 6),
    )
    return JumpEvents(
        up_jumps=up_jumps,
        down_jumps=down_jumps,
        threshold=threshold,
        detection_sigma=threshold_sigma,
    )


def fit_jump_distribution(jumps: np.ndarray, direction: str) -> JumpDistParams:
    """Fit a log-normal distribution to jump magnitudes.

    For down jumps the absolute values are used; sign is applied during simulation.
    """
    if len(jumps) < 2:
        logger.warning("insufficient_jumps_for_fit", direction=direction, count=len(jumps))
        return JumpDistParams(mu=0.0, sigma=0.01)

    magnitudes = np.abs(jumps)
    log_magnitudes = np.log(magnitudes + 1e-10)
    mu = float(np.mean(log_magnitudes))
    sigma = float(np.std(log_magnitudes))

    return JumpDistParams(mu=mu, sigma=sigma)


def compute_jump_ci(jumps: np.ndarray, confidence: float = 0.95) -> Optional[JumpCI]:
    """Compute confidence intervals for log-normal jump parameters.

    Uses Student-t CI for the mean and chi-squared CI for the std deviation
    of log-magnitudes. Returns None when fewer than 2 samples are available.
    """
    if len(jumps) < 2:
        return None

    magnitudes = np.abs(jumps)
    log_mags = np.log(magnitudes + 1e-10)
    n = len(log_mags)
    mu_hat = float(np.mean(log_mags))
    std_hat = float(np.std(log_mags, ddof=1))
    alpha = 1.0 - confidence

    # t-interval for the mean
    mu_low, mu_high = stats.t.interval(confidence, df=n - 1, loc=mu_hat, scale=std_hat / np.sqrt(n))

    # chi-squared interval for the std
    chi2_low = stats.chi2.ppf(alpha / 2, df=n - 1)
    chi2_high = stats.chi2.ppf(1 - alpha / 2, df=n - 1)
    sigma_low = float(np.sqrt((n - 1) * std_hat ** 2 / chi2_high))
    sigma_high = float(np.sqrt((n - 1) * std_hat ** 2 / chi2_low))

    return JumpCI(
        mu_low=float(mu_low),
        mu_high=float(mu_high),
        sigma_low=sigma_low,
        sigma_high=sigma_high,
    )


def estimate_jump_params(returns: np.ndarray, dt: float = 1.0, threshold_sigma: float = DEFAULT_JUMP_THRESHOLD_SIGMA) -> JumpParams:
    """Estimate full jump parameter set from historical returns, including 95% CIs."""
    events = detect_jumps(returns, threshold_sigma=threshold_sigma)
    n = len(returns)

    lambda_up = len(events.up_jumps) / (n * dt) if n > 0 else 0.0
    lambda_down = len(events.down_jumps) / (n * dt) if n > 0 else 0.0

    up_dist = fit_jump_distribution(events.up_jumps, "up")
    down_dist = fit_jump_distribution(np.abs(events.down_jumps), "down")
    ci_up = compute_jump_ci(events.up_jumps)
    ci_down = compute_jump_ci(events.down_jumps)

    return JumpParams(
        lambda_up=lambda_up,
        lambda_down=lambda_down,
        up=up_dist,
        down=down_dist,
        ci_up=ci_up,
        ci_down=ci_down,
    )


def compound_poisson_process(
    lambda_: float,
    dist_params: JumpDistParams,
    n_paths: int,
    dt: float,
    sign: float = 1.0,
) -> np.ndarray:
    """Sample one time step of a compound Poisson jump process.

    Returns an array of shape (n_paths,) with jump increments for this step.
    """
    jump_counts = np.random.poisson(lambda_ * dt, size=n_paths)
    increments = np.zeros(n_paths)

    active = jump_counts > 0
    if not active.any():
        return increments

    for i in np.where(active)[0]:
        n_jumps = jump_counts[i]
        sizes = np.random.lognormal(mean=dist_params.mu, sigma=dist_params.sigma, size=n_jumps)
        increments[i] = sign * np.sum(sizes)

    return increments
