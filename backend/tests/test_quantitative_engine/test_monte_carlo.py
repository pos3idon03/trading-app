"""Tests for the Monte Carlo simulation engine."""
import numpy as np
import pytest

from features.quantitative_engine.jump_diffusion import JumpDistParams, JumpParams
from features.quantitative_engine.monte_carlo import (
    DistributionData,
    SimulationResult,
    SimulationStats,
    compute_path_statistics,
    compute_return_distribution,
    extract_percentile_paths,
    run_simulation,
    simulate_paths,
)
from features.quantitative_engine.vasicek import VasicekParams


@pytest.fixture
def vasicek_params():
    return VasicekParams(k=0.1, theta=100.0, sigma=10.0)


@pytest.fixture
def jump_params():
    return JumpParams(
        lambda_up=5.0,
        lambda_down=5.0,
        up=JumpDistParams(mu=-3.0, sigma=0.5),
        down=JumpDistParams(mu=-3.0, sigma=0.5),
    )


class TestSimulatePaths:
    def test_output_shape(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=200)
        assert paths.shape == (51, 200)

    def test_first_row_is_s0(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=30, n_paths=100)
        assert np.all(paths[0] == 100.0)

    def test_reproducible_with_seed(self, vasicek_params, jump_params):
        p1 = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=30, n_paths=100, seed=42)
        p2 = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=30, n_paths=100, seed=42)
        np.testing.assert_array_equal(p1, p2)

    def test_different_seeds_produce_different_paths(self, vasicek_params, jump_params):
        p1 = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=30, n_paths=100, seed=1)
        p2 = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=30, n_paths=100, seed=2)
        assert not np.array_equal(p1, p2)


class TestComputePathStatistics:
    def test_returns_simulation_stats(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=500)
        stats = compute_path_statistics(paths, s0=100.0)
        assert isinstance(stats, SimulationStats)

    def test_percentile_ordering(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=1000)
        stats = compute_path_statistics(paths, s0=100.0)
        assert stats.p5 <= stats.p25 <= stats.p50 <= stats.p75 <= stats.p95

    def test_prob_positive_in_range(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=1000)
        stats = compute_path_statistics(paths, s0=100.0)
        assert 0.0 <= stats.prob_positive_return <= 1.0

    def test_mean_max_drawdown_is_negative(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=100, n_paths=500)
        stats = compute_path_statistics(paths, s0=100.0)
        assert stats.mean_max_drawdown <= 0.0


class TestExtractPercentilePaths:
    def test_returns_dict_with_all_percentiles(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=500)
        pct_paths = extract_percentile_paths(paths)
        for pct in ["5", "25", "50", "75", "95"]:
            assert pct in pct_paths
            assert len(pct_paths[pct]) == 51


class TestRunSimulation:
    def test_end_to_end(self, vasicek_params, jump_params):
        result = run_simulation(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=200, seed=0)
        assert isinstance(result, SimulationResult)
        assert result.duration_ms > 0
        assert result.stats is not None
        assert result.percentile_paths is not None


class TestComputeReturnDistribution:
    def test_returns_distribution_data(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=300, seed=1)
        dist = compute_return_distribution(paths, vasicek_params, jump_params)
        assert isinstance(dist, DistributionData)

    def test_histogram_is_non_empty(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=300, seed=1)
        dist = compute_return_distribution(paths, vasicek_params, jump_params)
        assert len(dist.histogram) > 0

    def test_histogram_densities_are_non_negative(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=300, seed=2)
        dist = compute_return_distribution(paths, vasicek_params, jump_params)
        assert all(d >= 0 for _, d in dist.histogram)

    def test_mr_density_same_length_as_grid(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=300, seed=3)
        dist = compute_return_distribution(paths, vasicek_params, jump_params)
        assert len(dist.mr_density) == 200

    def test_jump_densities_have_grid_length(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=300, seed=4)
        dist = compute_return_distribution(paths, vasicek_params, jump_params)
        assert len(dist.jump_up_density) == 200
        assert len(dist.jump_down_density) == 200

    def test_mr_densities_are_non_negative(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=300, seed=5)
        dist = compute_return_distribution(paths, vasicek_params, jump_params)
        assert all(d >= 0 for _, d in dist.mr_density)

    def test_custom_n_bins(self, vasicek_params, jump_params):
        paths = simulate_paths(vasicek_params, jump_params, s0=100.0, dt=1/252, steps=50, n_paths=300, seed=6)
        dist = compute_return_distribution(paths, vasicek_params, jump_params, n_bins=30)
        assert len(dist.histogram) == 30
