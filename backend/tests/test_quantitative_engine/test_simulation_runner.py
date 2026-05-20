"""Tests for simulation runner dispatch."""
from datetime import datetime, timezone

from dtos.simulation_dto import (
    CalibratedModelParams,
    JumpParams,
    MertonParams,
    OuDeviationParams,
    VasicekParams,
)
from features.quantitative_engine.simulation_runner import dispatch_mc_simulation


def _calibrated() -> CalibratedModelParams:
    jumps = JumpParams(
        lambda_up=0.0,
        lambda_down=0.0,
        mu_up=-10.0,
        sigma_up=0.01,
        mu_down=-10.0,
        sigma_down=0.01,
    )
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return CalibratedModelParams(
        vasicek=VasicekParams(k=0.5, theta=100.0, sigma=2.0, mu=0.0),
        jumps=jumps,
        calibration_start=now,
        calibration_end=now,
        num_observations=100,
        last_price=100.0,
        merton=MertonParams(mu=0.05, sigma=0.2),
        ou_deviation=OuDeviationParams(
            kappa=2.0,
            theta=0.0,
            sigma=0.1,
            ma_window=20,
            ma_level=100.0,
            x0=0.0,
        ),
    )


class TestDispatchMcSimulation:
    def test_merton_dispatch(self):
        result = dispatch_mc_simulation(_calibrated(), "merton", 200, 5, "1d")
        assert 0.0 <= result.stats.prob_positive_return <= 1.0

    def test_ou_deviation_dispatch(self):
        result = dispatch_mc_simulation(_calibrated(), "ou_deviation", 200, 5, "1d")
        assert 0.0 <= result.stats.prob_positive_return <= 1.0

    def test_blended_dispatch(self):
        result = dispatch_mc_simulation(
            _calibrated(), "blended", 200, 5, "1d", adx=20.0,
        )
        assert 0.0 <= result.stats.prob_positive_return <= 1.0

    def test_vasicek_dispatch(self):
        result = dispatch_mc_simulation(_calibrated(), "vasicek", 200, 5, "1d")
        assert 0.0 <= result.stats.prob_positive_return <= 1.0
