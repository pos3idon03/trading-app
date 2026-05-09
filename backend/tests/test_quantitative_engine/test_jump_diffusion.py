"""Tests for jump diffusion parameter estimation."""
import numpy as np
import pytest

from features.quantitative_engine.jump_diffusion import (
    JumpDistParams,
    JumpParams,
    compound_poisson_process,
    detect_jumps,
    estimate_jump_params,
    fit_jump_distribution,
)


class TestDetectJumps:
    def test_returns_jump_events(self, sample_log_returns):
        events = detect_jumps(sample_log_returns)
        assert hasattr(events, "up_jumps")
        assert hasattr(events, "down_jumps")

    def test_extreme_return_detected_as_jump(self):
        returns = np.zeros(200)
        returns[100] = 0.25
        returns[150] = -0.20
        events = detect_jumps(returns, threshold_sigma=2.0)
        assert len(events.up_jumps) >= 1
        assert len(events.down_jumps) >= 1

    def test_no_jumps_in_flat_series(self):
        returns = np.full(100, 0.001)
        events = detect_jumps(returns, threshold_sigma=2.0)
        assert len(events.up_jumps) == 0
        assert len(events.down_jumps) == 0


class TestFitJumpDistribution:
    def test_returns_params(self):
        jumps = np.array([0.05, 0.08, 0.06, 0.10, 0.07])
        params = fit_jump_distribution(jumps, "up")
        assert isinstance(params, JumpDistParams)
        assert params.sigma > 0

    def test_insufficient_jumps_returns_default(self):
        params = fit_jump_distribution(np.array([0.05]), "up")
        assert params.sigma == 0.01


class TestEstimateJumpParams:
    def test_returns_jump_params(self, sample_log_returns):
        params = estimate_jump_params(sample_log_returns)
        assert isinstance(params, JumpParams)

    def test_lambda_is_non_negative(self, sample_log_returns):
        params = estimate_jump_params(sample_log_returns)
        assert params.lambda_up >= 0
        assert params.lambda_down >= 0


class TestCompoundPoissonProcess:
    def test_returns_correct_shape(self):
        dist = JumpDistParams(mu=-3.0, sigma=0.5)
        result = compound_poisson_process(2.0, dist, n_paths=1000, dt=1/252)
        assert result.shape == (1000,)

    def test_zero_lambda_produces_zeros(self):
        dist = JumpDistParams(mu=-3.0, sigma=0.5)
        result = compound_poisson_process(0.0, dist, n_paths=500, dt=1/252)
        assert np.all(result == 0)

    def test_high_lambda_produces_nonzero(self):
        dist = JumpDistParams(mu=-2.0, sigma=0.3)
        result = compound_poisson_process(1000.0, dist, n_paths=500, dt=1.0, sign=1.0)
        assert np.any(result != 0)
