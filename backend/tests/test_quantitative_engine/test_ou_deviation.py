"""Tests for OU deviation model."""
import numpy as np
import pytest

from features.quantitative_engine.jump_diffusion import JumpDistParams, JumpParams
from features.quantitative_engine.ou_deviation import (
    OuDeviationParams,
    estimate_ou_deviation_params,
    run_ou_deviation_simulation,
    run_single_step_ou_prob,
)


def _flat_jumps() -> JumpParams:
    tiny = JumpDistParams(mu=-10.0, sigma=0.01)
    return JumpParams(lambda_up=0.0, lambda_down=0.0, up=tiny, down=tiny)


def _mean_reverting_prices(n: int = 200, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    ma = 100.0
    kappa = 0.15
    prices = [ma]
    for _ in range(n - 1):
        shock = rng.normal(0, 0.5)
        prices.append(prices[-1] + kappa * (ma - prices[-1]) + shock)
    return np.array(prices, dtype=float)


class TestEstimateOuDeviationParams:
    def test_returns_params(self):
        prices = _mean_reverting_prices()
        params = estimate_ou_deviation_params(prices, ma_window=20, dt=1 / 252)
        assert isinstance(params, OuDeviationParams)
        assert params.kappa > 0
        assert params.sigma > 0
        assert params.ma_level > 0

    def test_raises_on_short_series(self):
        with pytest.raises(ValueError, match="at least"):
            estimate_ou_deviation_params(np.linspace(100, 101, 40), ma_window=20, dt=1 / 252)


class TestOuDeviationProb:
    def test_extended_above_ma_lower_prob(self):
        prices = _mean_reverting_prices(250)
        base = estimate_ou_deviation_params(prices, ma_window=20, dt=1 / 252)
        jumps = _flat_jumps()

        at_ma = OuDeviationParams(
            kappa=base.kappa,
            theta=base.theta,
            sigma=base.sigma * 0.5,
            ma_window=base.ma_window,
            ma_level=base.ma_level,
            x0=0.0,
        )
        extended = OuDeviationParams(
            kappa=base.kappa,
            theta=base.theta,
            sigma=base.sigma * 0.5,
            ma_window=base.ma_window,
            ma_level=base.ma_level,
            x0=0.05,
        )

        s0_at = base.ma_level
        s0_ext = base.ma_level * np.exp(0.05)
        prob_at = run_single_step_ou_prob(at_ma, jumps, s0_at, 1 / 252, n_paths=3000, seed=1)
        prob_ext = run_single_step_ou_prob(extended, jumps, s0_ext, 1 / 252, n_paths=3000, seed=1)
        assert prob_ext < prob_at

    def test_below_ma_higher_prob(self):
        prices = _mean_reverting_prices(250)
        base = estimate_ou_deviation_params(prices, ma_window=20, dt=1 / 252)
        jumps = _flat_jumps()

        below = OuDeviationParams(
            kappa=base.kappa,
            theta=base.theta,
            sigma=base.sigma * 0.5,
            ma_window=base.ma_window,
            ma_level=base.ma_level,
            x0=-0.05,
        )
        s0_below = base.ma_level * np.exp(-0.05)
        prob_below = run_single_step_ou_prob(below, jumps, s0_below, 1 / 252, n_paths=3000, seed=2)
        assert prob_below > 0.5

    def test_simulation_returns_stats(self):
        prices = _mean_reverting_prices()
        params = estimate_ou_deviation_params(prices, ma_window=20, dt=1 / 252)
        result = run_ou_deviation_simulation(
            params, _flat_jumps(), float(prices[-1]), 1 / 252, steps=5, n_paths=500, seed=3,
        )
        assert 0.0 <= result.stats.prob_positive_return <= 1.0
        assert len(result.percentile_paths) == 5
