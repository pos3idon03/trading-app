"""Tests for MC simulation walk-forward optimizer."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from features.quantitative_engine.mc_simulation_optimizer import (
    MAX_COMBOS,
    _oos_predictive_score,
    validate_param_grid,
    walk_forward_mc_simulation_optimize,
)
from features.quantitative_engine.monte_carlo import SimulationResult, SimulationStats


def _make_stats(**overrides) -> SimulationStats:
    defaults = dict(
        mean_terminal=110.0,
        std_terminal=5.0,
        p5=100.0,
        p25=105.0,
        p50=110.0,
        p75=115.0,
        p95=120.0,
        prob_positive_return=0.65,
        mean_max_drawdown=-0.12,
    )
    defaults.update(overrides)
    return SimulationStats(**defaults)


def _make_sim_result(stats: SimulationStats | None = None) -> SimulationResult:
    stats = stats or _make_stats()
    paths = np.linspace(100.0, stats.p50, 11).reshape(11, 1)
    return SimulationResult(paths=paths, stats=stats, percentile_paths={"50": paths[:, 0].tolist()}, duration_ms=1.0)


def _make_price_df(n: int = 200) -> pd.DataFrame:
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    times = [start + timedelta(days=i) for i in range(n)]
    closes = 100 + np.cumsum(np.random.default_rng(42).normal(0, 0.5, n))
    return pd.DataFrame({"time": times, "close": closes})


class TestValidateParamGrid:
    def test_generates_combinations(self):
        combos = validate_param_grid({"num_paths": [500, 1000], "calibration_years": [5, 10]})
        assert len(combos) == 4

    def test_rejects_unknown_keys(self):
        with pytest.raises(ValueError, match="Unsupported"):
            validate_param_grid({"fast_window": [5, 10]})

    def test_rejects_too_many_combos(self):
        grid = {"num_paths": list(range(100, 100 + MAX_COMBOS + 1))}
        with pytest.raises(ValueError, match="Too many combinations"):
            validate_param_grid(grid)

    def test_rejects_invalid_num_paths(self):
        with pytest.raises(ValueError, match="num_paths"):
            validate_param_grid({"num_paths": [50]})


class TestOosPredictiveScore:
    def test_prob_positive_return(self):
        sim = _make_sim_result()
        closes = np.array([100.0, 105.0, 112.0])
        assert _oos_predictive_score(closes, sim, 100.0, "prob_positive_return") == 1.0

    def test_p50_penalizes_error(self):
        sim = _make_sim_result(_make_stats(p50=120.0))
        closes = np.array([100.0, 110.0])
        score = _oos_predictive_score(closes, sim, 100.0, "p50")
        assert score < 0


class TestWalkForwardMcSimulationOptimize:
    @patch("features.quantitative_engine.mc_simulation_optimizer.dispatch_mc_simulation")
    @patch("features.quantitative_engine.mc_simulation_optimizer.calibrate_at_date")
    def test_returns_best_params(self, mock_calibrate, mock_dispatch):
        mock_calibrate.return_value = MagicMock(last_price=100.0)
        mock_dispatch.return_value = _make_sim_result()

        df = _make_price_df(200)
        grid = {"num_paths": [500, 1000], "calibration_years": [5, 10]}
        result = walk_forward_mc_simulation_optimize(
            df, grid, n_splits=2, model_type="merton", timeframe="1d",
            horizon_steps=21, optimize_metric="prob_positive_return",
        )

        assert result.best_params in [
            {"num_paths": 500, "calibration_years": 5},
            {"num_paths": 500, "calibration_years": 10},
            {"num_paths": 1000, "calibration_years": 5},
            {"num_paths": 1000, "calibration_years": 10},
        ]
        assert len(result.all_results) == 4
        assert result.n_splits == 2

    def test_insufficient_data_raises(self):
        df = _make_price_df(10)
        with pytest.raises(ValueError, match="Insufficient data"):
            walk_forward_mc_simulation_optimize(
                df, {"num_paths": [500]}, n_splits=5, model_type="merton",
                timeframe="1d", horizon_steps=21, optimize_metric="prob_positive_return",
            )

    def test_invalid_metric_raises(self):
        df = _make_price_df(200)
        with pytest.raises(ValueError, match="Unsupported optimize_metric"):
            walk_forward_mc_simulation_optimize(
                df, {"num_paths": [500]}, n_splits=2, model_type="merton",
                timeframe="1d", horizon_steps=21, optimize_metric="sharpe_ratio",
            )
