"""Tests for jump diffusion parameter estimation."""
import numpy as np
import pytest

from features.quantitative_engine.jump_diffusion import (
    JumpCI,
    JumpDistParams,
    JumpParams,
    compound_poisson_process,
    compute_jump_ci,
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


class TestComputeJumpCI:
    def test_returns_jump_ci_with_sufficient_data(self):
        jumps = np.array([0.05, 0.08, 0.06, 0.10, 0.07, 0.09, 0.04, 0.12, 0.06, 0.08])
        ci = compute_jump_ci(jumps)
        assert isinstance(ci, JumpCI)

    def test_ci_bounds_are_ordered(self):
        jumps = np.array([0.05, 0.08, 0.06, 0.10, 0.07, 0.09, 0.04, 0.12, 0.06, 0.08])
        ci = compute_jump_ci(jumps)
        assert ci.mu_low < ci.mu_high
        assert ci.sigma_low < ci.sigma_high

    def test_returns_none_with_single_sample(self):
        ci = compute_jump_ci(np.array([0.05]))
        assert ci is None

    def test_returns_none_with_empty_array(self):
        ci = compute_jump_ci(np.array([]))
        assert ci is None

    def test_sigma_ci_is_positive(self):
        jumps = np.array([0.05, 0.08, 0.06, 0.10, 0.07, 0.09])
        ci = compute_jump_ci(jumps)
        assert ci.sigma_low > 0
        assert ci.sigma_high > 0

    def test_custom_confidence(self):
        jumps = np.array([0.05, 0.08, 0.06, 0.10, 0.07, 0.09, 0.04, 0.12])
        ci_95 = compute_jump_ci(jumps, confidence=0.95)
        ci_99 = compute_jump_ci(jumps, confidence=0.99)
        assert (ci_99.mu_high - ci_99.mu_low) > (ci_95.mu_high - ci_95.mu_low)


class TestEstimateJumpParamsCI:
    def test_ci_populated_when_enough_jumps(self):
        returns = np.zeros(500)
        rng = np.random.default_rng(42)
        # Inject obvious up and down jumps
        returns[rng.choice(500, 20, replace=False)] = 0.25
        returns[rng.choice(500, 20, replace=False)] = -0.25
        params = estimate_jump_params(returns, threshold_sigma=2.0)
        assert params.ci_up is not None
        assert params.ci_down is not None

    def test_ci_none_when_insufficient_jumps(self):
        returns = np.zeros(100)
        returns[50] = 0.25  # only one up jump
        params = estimate_jump_params(returns, threshold_sigma=2.0)
        assert params.ci_up is None


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
