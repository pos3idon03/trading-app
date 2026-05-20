"""Tests for blended MC probability."""
from datetime import datetime, timezone

import numpy as np
import pytest

from dtos.simulation_dto import (
    CalibratedModelParams,
    JumpParams,
    MertonParams,
    OuDeviationParams,
    VasicekParams,
)
from features.quantitative_engine.blended_prob import run_blended_step_prob
from features.quantitative_engine.regime_weight import trend_weight_from_adx


def _sample_calibrated() -> CalibratedModelParams:
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


class TestRunBlendedStepProb:
    def test_high_adx_near_trend_prob(self):
        params = _sample_calibrated()
        high = run_blended_step_prob(params, 100.0, 1 / 252, 500, adx=30.0, seed=1)
        low_adx = run_blended_step_prob(params, 100.0, 1 / 252, 500, adx=10.0, seed=1)
        assert high.regime_weight == 1.0
        assert low_adx.regime_weight == 0.0
        assert high.prob_effective == pytest.approx(high.prob_trend, rel=1e-6)
        assert low_adx.prob_effective == pytest.approx(low_adx.prob_reversion, rel=1e-6)

    def test_mid_adx_blends(self):
        params = _sample_calibrated()
        result = run_blended_step_prob(params, 100.0, 1 / 252, 500, adx=20.0, seed=2)
        w = trend_weight_from_adx(20.0)
        expected = w * result.prob_trend + (1 - w) * result.prob_reversion
        assert result.prob_effective == pytest.approx(expected, rel=1e-6)
        assert result.regime_weight == pytest.approx(w, rel=1e-6)

    def test_w_trend_override(self):
        params = _sample_calibrated()
        high = run_blended_step_prob(
            params, 100.0, 1 / 252, 200, adx=10.0, w_trend_override=0.9,
        )
        assert high.regime_weight == pytest.approx(0.9, rel=1e-6)

    def test_missing_params_raises(self):
        params = _sample_calibrated()
        params.ou_deviation = None
        with pytest.raises(ValueError, match="ou_deviation"):
            run_blended_step_prob(params, 100.0, 1 / 252, 100, adx=20.0)
