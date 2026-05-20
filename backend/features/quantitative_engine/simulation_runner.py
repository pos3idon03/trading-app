"""Shared Monte Carlo simulation dispatch (no DB persistence)."""
from dtos.simulation_dto import CalibratedModelParams
from features.quantitative_engine.blended_prob import run_blended_simulation
from features.quantitative_engine.jump_diffusion import JumpDistParams, JumpParams
from features.quantitative_engine.merton_jump_diffusion import MertonParams, run_merton_simulation
from features.quantitative_engine.monte_carlo import SimulationResult, run_simulation
from features.quantitative_engine.ou_deviation import OuDeviationParams, run_ou_deviation_simulation
from features.quantitative_engine.regime_weight import calc_adx
from features.quantitative_engine.vasicek import VasicekParams


def timeframe_to_dt(timeframe: str) -> float:
    mapping = {
        "1m": 1 / 252 / 390,
        "5m": 5 / 252 / 390,
        "15m": 15 / 252 / 390,
        "30m": 30 / 252 / 390,
        "1h": 1 / 252 / 6.5,
        "4h": 4 / 252 / 6.5,
        "1d": 1 / 252,
        "1w": 1 / 52,
    }
    return mapping.get(timeframe, 1 / 252)


def _to_vasicek(dto) -> VasicekParams:
    return VasicekParams(k=dto.k, theta=dto.theta, sigma=dto.sigma, mu=dto.mu)


def _to_merton(dto) -> MertonParams:
    return MertonParams(mu=dto.mu, sigma=dto.sigma)


def _to_ou(dto, s0: float) -> OuDeviationParams:
    import numpy as np

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


def _to_jumps(dto) -> JumpParams:
    return JumpParams(
        lambda_up=dto.lambda_up,
        lambda_down=dto.lambda_down,
        up=JumpDistParams(mu=dto.mu_up, sigma=dto.sigma_up),
        down=JumpDistParams(mu=dto.mu_down, sigma=dto.sigma_down),
    )


def dispatch_mc_simulation(
    calibrated: CalibratedModelParams,
    model_type: str,
    num_paths: int,
    horizon_steps: int,
    timeframe: str,
    adx: float | None = None,
    adx_trend_threshold: float = 25.0,
) -> SimulationResult:
    """Run MC simulation from calibrated params without persisting to DB."""
    dt = timeframe_to_dt(timeframe)
    s0 = calibrated.last_price
    jumps = _to_jumps(calibrated.jumps)

    if model_type == "blended":
        if calibrated.merton is None or calibrated.ou_deviation is None:
            raise ValueError("Blended model requires merton and ou_deviation params")
        if adx is None:
            adx = 20.0
        return run_blended_simulation(
            calibrated, s0, dt, horizon_steps, num_paths, adx,
            adx_high=adx_trend_threshold,
        )

    if model_type == "ou_deviation":
        if calibrated.ou_deviation is None:
            raise ValueError("OU deviation params not available; re-run calibration")
        return run_ou_deviation_simulation(
            _to_ou(calibrated.ou_deviation, s0), jumps, s0, dt, horizon_steps, num_paths,
        )

    if model_type == "merton":
        if calibrated.merton is None:
            raise ValueError("Merton params not available; re-run calibration")
        return run_merton_simulation(_to_merton(calibrated.merton), jumps, s0, dt, horizon_steps, num_paths)

    return run_simulation(_to_vasicek(calibrated.vasicek), jumps, s0, dt, horizon_steps, num_paths)


def adx_from_ohlcv(df, period: int = 14) -> float:
    """Latest ADX value from an OHLCV dataframe."""
    adx = calc_adx(
        df["high"].astype(float),
        df["low"].astype(float),
        df["close"].astype(float),
        period=period,
    )
    val = float(adx.iloc[-1])
    return val if val == val else 20.0
