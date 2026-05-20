"""Orchestrates model calibration: fetch data → estimate params → persist."""
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

McModelType = Literal["vasicek", "merton", "ou_deviation", "blended"]

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_ohlcv
from dtos.simulation_dto import CalibratedModelParams, JumpCI, JumpParams, MertonParams, OuDeviationParams, VasicekParams
from features.quantitative_engine.jump_diffusion import estimate_jump_params
from features.quantitative_engine.ou_deviation import estimate_ou_deviation_params
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
    ou_ma_window: int = 20,
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
    result = calibrate_from_prices(prices, timeframe, start, end, ou_ma_window=ou_ma_window)
    logger.info(
        "model_calibrated",
        asset_id=asset_id,
        timeframe=timeframe,
        n_obs=len(prices),
        vasicek_k=round(result.vasicek.k, 6),
        merton_mu=round(result.merton.mu, 6) if result.merton else None,
        merton_sigma=round(result.merton.sigma, 6) if result.merton else None,
    )
    return result


def _needs_ou_calibration(model_type: McModelType | None) -> bool:
    return model_type in (None, "ou_deviation", "blended")


def min_calibration_price_bars(model_type: McModelType | None, ou_ma_window: int = 20) -> int:
    """Minimum close prices required in the calibration slice."""
    base = 30
    if _needs_ou_calibration(model_type):
        return base + ou_ma_window
    return base


def calibrate_from_prices(
    prices: np.ndarray,
    timeframe: str,
    start: datetime,
    end: datetime,
    ou_ma_window: int = 20,
    model_type: McModelType | None = None,
) -> CalibratedModelParams:
    """Fit model parameters from a close-price array (in-memory calibration)."""
    min_bars = min_calibration_price_bars(model_type, ou_ma_window)
    if len(prices) < min_bars:
        raise ValueError(
            f"Insufficient data for calibration: {len(prices)} price bars "
            f"(need {min_bars}+ for model_type={model_type or 'all'})"
        )

    dt = _timeframe_to_dt(timeframe)
    log_returns = np.diff(np.log(prices))

    vasicek_raw = calibrate_vasicek(prices, dt=dt)
    jump_raw = estimate_jump_params(log_returns, dt=dt)

    vasicek_dto = VasicekParams(
        k=vasicek_raw.k, theta=vasicek_raw.theta, sigma=vasicek_raw.sigma, mu=vasicek_raw.mu,
    )
    merton_dto = _calibrate_merton_params(log_returns, dt)
    ou_dto: OuDeviationParams | None = None
    if _needs_ou_calibration(model_type):
        try:
            ou_raw = estimate_ou_deviation_params(prices, ma_window=ou_ma_window, dt=dt)
        except ValueError as exc:
            raise ValueError(
                f"{exc}. For intraday OU/blended, increase calibration_days "
                f"(need roughly {min_bars}+ {timeframe} bars) or lower ou_ma_window."
            ) from exc
        ou_dto = OuDeviationParams(
            kappa=ou_raw.kappa,
            theta=ou_raw.theta,
            sigma=ou_raw.sigma,
            ma_window=ou_raw.ma_window,
            ma_level=ou_raw.ma_level,
            x0=ou_raw.x0,
        )

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

    return CalibratedModelParams(
        vasicek=vasicek_dto,
        jumps=jump_dto,
        calibration_start=start,
        calibration_end=end,
        num_observations=len(prices),
        last_price=float(prices[-1]),
        merton=merton_dto,
        ou_deviation=ou_dto,
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
