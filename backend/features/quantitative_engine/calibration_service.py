"""Orchestrates model calibration: fetch data → estimate params → persist."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_ohlcv
from dtos.simulation_dto import CalibratedModelParams, JumpCI, JumpParams, MertonParams, VasicekParams
from features.quantitative_engine.jump_diffusion import estimate_jump_params
from features.quantitative_engine.vasicek import calibrate_vasicek, estimate_drift_rate
from utils.logging import get_logger
from utils.time_utils import utcnow

logger = get_logger(__name__)

DEFAULT_CALIBRATION_YEARS = 10


def _default_start(years: int = DEFAULT_CALIBRATION_YEARS) -> datetime:
    return utcnow() - timedelta(days=years * 365)


async def calibrate_model_for_asset(
    session: AsyncSession,
    asset_id: int,
    timeframe: str = "1d",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    calibration_years: Optional[int] = None,
) -> CalibratedModelParams:
    """Fetch stored OHLCV and fit both Vasicek+Jump and Merton+Jump parameters.

    Both model parameter sets are always computed from the same price series so
    that the caller can dispatch on model_type without a second DB round-trip.
    """
    start = start or _default_start(calibration_years or DEFAULT_CALIBRATION_YEARS)
    end = end or utcnow()

    df = await get_ohlcv(session, asset_id, timeframe, start, end)
    if df.empty or len(df) < 30:
        raise ValueError(f"Insufficient data for calibration: {len(df)} rows (need 30+)")

    prices = df["close"].to_numpy(dtype=float)
    dt = _timeframe_to_dt(timeframe)
    log_returns = np.diff(np.log(prices))

    vasicek_raw = calibrate_vasicek(prices, dt=dt)
    jump_raw = estimate_jump_params(log_returns, dt=dt)

    vasicek_dto = VasicekParams(k=vasicek_raw.k, theta=vasicek_raw.theta, sigma=vasicek_raw.sigma, mu=vasicek_raw.mu)
    merton_dto = _calibrate_merton_params(log_returns, dt)

    ci_up = JumpCI(**vars(jump_raw.ci_up)) if jump_raw.ci_up else None
    ci_down = JumpCI(**vars(jump_raw.ci_down)) if jump_raw.ci_down else None

    jump_dto = JumpParams(
        lambda_up=jump_raw.lambda_up,
        lambda_down=jump_raw.lambda_down,
        mu_up=jump_raw.up.mu,
        sigma_up=jump_raw.up.sigma,
        mu_down=jump_raw.down.mu,
        sigma_down=jump_raw.down.sigma,
        ci_up=ci_up,
        ci_down=ci_down,
    )

    logger.info(
        "model_calibrated",
        asset_id=asset_id,
        timeframe=timeframe,
        n_obs=len(prices),
        vasicek_k=round(vasicek_raw.k, 6),
        merton_mu=round(merton_dto.mu, 6),
        merton_sigma=round(merton_dto.sigma, 6),
    )
    return CalibratedModelParams(
        vasicek=vasicek_dto,
        jumps=jump_dto,
        calibration_start=start,
        calibration_end=end,
        num_observations=len(prices),
        last_price=float(prices[-1]),
        merton=merton_dto,
    )


def _calibrate_merton_params(log_returns: np.ndarray, dt: float) -> MertonParams:
    """Estimate Merton GBM parameters from log-returns.

    mu    = annualized mean log-return = mean(r) / dt
    sigma = annualized volatility      = std(r)  / sqrt(dt)
    """
    mu = float(np.mean(log_returns) / dt)
    sigma = float(np.std(log_returns) / np.sqrt(dt))
    return MertonParams(mu=mu, sigma=sigma)


def _timeframe_to_dt(timeframe: str) -> float:
    """Convert timeframe string to dt as a fraction of one trading year."""
    trading_seconds_per_year = 252 * 6.5 * 3600
    mapping = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 14400,
        "1d": 252 ** -1,  # already in year fractions
        "1w": 52 ** -1,
    }
    if timeframe in ("1d", "1w"):
        return mapping[timeframe]
    return mapping.get(timeframe, 3600) / trading_seconds_per_year
