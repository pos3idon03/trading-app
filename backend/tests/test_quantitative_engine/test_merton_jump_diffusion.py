"""Tests for Merton Jump-Diffusion simulation engine and calibration integration."""
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from features.quantitative_engine.jump_diffusion import JumpDistParams, JumpParams
from features.quantitative_engine.merton_jump_diffusion import (
    MertonParams,
    run_merton_simulation,
    simulate_merton_paths,
)
from features.quantitative_engine.monte_carlo import SimulationResult


@pytest.fixture
def merton_params():
    return MertonParams(mu=0.10, sigma=0.20)


@pytest.fixture
def merton_params_zero_drift():
    return MertonParams(mu=0.0, sigma=0.20)


@pytest.fixture
def jump_params():
    return JumpParams(
        lambda_up=5.0,
        lambda_down=5.0,
        up=JumpDistParams(mu=-3.0, sigma=0.5),
        down=JumpDistParams(mu=-3.0, sigma=0.5),
    )


class TestSimulateMertonPaths:
    def test_output_shape(self, merton_params, jump_params):
        paths = simulate_merton_paths(merton_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=200)
        assert paths.shape == (51, 200)

    def test_first_row_equals_s0(self, merton_params, jump_params):
        paths = simulate_merton_paths(merton_params, jump_params, s0=150.0, dt=1/252, steps=30, n_paths=100)
        assert np.all(paths[0] == 150.0)

    def test_paths_are_non_negative(self, merton_params, jump_params):
        """Multiplicative diffusion + floor at 0 must keep paths non-negative."""
        paths = simulate_merton_paths(merton_params, jump_params, s0=100.0, dt=1/252, steps=252, n_paths=500, seed=0)
        assert np.all(paths >= 0.0)

    def test_reproducible_with_seed(self, merton_params, jump_params):
        p1 = simulate_merton_paths(merton_params, jump_params, s0=100.0, dt=1/252, steps=30, n_paths=100, seed=42)
        p2 = simulate_merton_paths(merton_params, jump_params, s0=100.0, dt=1/252, steps=30, n_paths=100, seed=42)
        np.testing.assert_array_equal(p1, p2)

    def test_different_seeds_produce_different_paths(self, merton_params, jump_params):
        p1 = simulate_merton_paths(merton_params, jump_params, s0=100.0, dt=1/252, steps=30, n_paths=100, seed=1)
        p2 = simulate_merton_paths(merton_params, jump_params, s0=100.0, dt=1/252, steps=30, n_paths=100, seed=2)
        assert not np.array_equal(p1, p2)

    def test_positive_drift_raises_mean_terminal(self, merton_params_zero_drift, jump_params):
        """Mean terminal with positive drift must exceed mean terminal with zero drift."""
        positive = MertonParams(mu=0.30, sigma=0.20)
        steps, n_paths, dt = 252, 2000, 1 / 252
        p_zero = simulate_merton_paths(merton_params_zero_drift, jump_params, s0=100.0, dt=dt, steps=steps, n_paths=n_paths, seed=42)
        p_positive = simulate_merton_paths(positive, jump_params, s0=100.0, dt=dt, steps=steps, n_paths=n_paths, seed=42)
        assert p_positive[-1].mean() > p_zero[-1].mean()

    def test_multiplicative_scaling_with_s0(self, merton_params, jump_params):
        """Terminal std dev must scale proportionally with initial price."""
        p_low = simulate_merton_paths(merton_params, jump_params, s0=100.0, dt=1/252, steps=252, n_paths=2000, seed=0)
        p_high = simulate_merton_paths(merton_params, jump_params, s0=200.0, dt=1/252, steps=252, n_paths=2000, seed=0)
        std_low = np.std(p_low[-1])
        std_high = np.std(p_high[-1])
        assert std_high > std_low


class TestRunMertonSimulation:
    def test_returns_simulation_result(self, merton_params, jump_params):
        result = run_merton_simulation(merton_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=200, seed=0)
        assert isinstance(result, SimulationResult)

    def test_stats_are_populated(self, merton_params, jump_params):
        result = run_merton_simulation(merton_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=200, seed=0)
        assert result.stats is not None
        assert result.stats.p5 <= result.stats.p50 <= result.stats.p95

    def test_percentile_paths_present(self, merton_params, jump_params):
        result = run_merton_simulation(merton_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=300, seed=1)
        for pct in ["5", "25", "50", "75", "95"]:
            assert pct in result.percentile_paths
            assert len(result.percentile_paths[pct]) == 51

    def test_duration_ms_positive(self, merton_params, jump_params):
        result = run_merton_simulation(merton_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=200, seed=0)
        assert result.duration_ms > 0

    def test_prob_positive_return_in_range(self, merton_params, jump_params):
        result = run_merton_simulation(merton_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=1000, seed=5)
        assert 0.0 <= result.stats.prob_positive_return <= 1.0


def _make_ohlcv_df(prices: np.ndarray):
    import pandas as pd
    from datetime import datetime, timedelta, timezone

    n = len(prices)
    dates = [datetime(2018, 1, 1, tzinfo=timezone.utc) + timedelta(days=i) for i in range(n)]
    return pd.DataFrame({
        "time": dates,
        "open": prices * 0.999,
        "high": prices * 1.005,
        "low": prices * 0.995,
        "close": prices,
        "volume": np.ones(n, dtype=int) * 1_000_000,
        "source": "test",
    })


@pytest.fixture
def trending_prices():
    rng = np.random.default_rng(99)
    returns = rng.normal(0.0006, 0.015, 500)
    return 100.0 * np.cumprod(1 + returns)


@pytest.mark.asyncio
async def test_calibration_populates_merton_params(trending_prices):
    """calibrate_model_for_asset must populate the merton field."""
    from features.quantitative_engine.calibration_service import calibrate_model_for_asset

    df = _make_ohlcv_df(trending_prices)
    mock_session = AsyncMock()
    with patch("features.quantitative_engine.calibration_service.get_ohlcv", return_value=df):
        result = await calibrate_model_for_asset(mock_session, asset_id=1, timeframe="1d")

    assert result.merton is not None
    assert isinstance(result.merton.mu, float)
    assert isinstance(result.merton.sigma, float)


@pytest.mark.asyncio
async def test_merton_sigma_is_positive(trending_prices):
    """Merton sigma (annualized vol) must always be positive."""
    from features.quantitative_engine.calibration_service import calibrate_model_for_asset

    df = _make_ohlcv_df(trending_prices)
    mock_session = AsyncMock()
    with patch("features.quantitative_engine.calibration_service.get_ohlcv", return_value=df):
        result = await calibrate_model_for_asset(mock_session, asset_id=1, timeframe="1d")

    assert result.merton.sigma > 0.0


@pytest.mark.asyncio
async def test_merton_mu_matches_annualized_drift(trending_prices):
    """Merton mu must equal mean(log_returns) / dt."""
    from features.quantitative_engine.calibration_service import calibrate_model_for_asset

    df = _make_ohlcv_df(trending_prices)
    mock_session = AsyncMock()
    with patch("features.quantitative_engine.calibration_service.get_ohlcv", return_value=df):
        result = await calibrate_model_for_asset(mock_session, asset_id=1, timeframe="1d")

    prices = trending_prices
    log_returns = np.diff(np.log(prices))
    dt = 1.0 / 252
    expected_mu = float(np.mean(log_returns) / dt)
    assert result.merton.mu == pytest.approx(expected_mu, rel=1e-6)
