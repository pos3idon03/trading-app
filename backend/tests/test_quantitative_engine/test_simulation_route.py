"""Tests for simulation DTO validation and monte_carlo route symbol resolution."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from dtos.simulation_dto import SimulationRequest


# ---------------------------------------------------------------------------
# SimulationRequest DTO validation
# ---------------------------------------------------------------------------

class TestSimulationRequestDTO:
    def test_accepts_asset_id_only(self):
        req = SimulationRequest(asset_id=1)
        assert req.asset_id == 1
        assert req.symbol is None

    def test_accepts_symbol_only(self):
        req = SimulationRequest(symbol="AAPL")
        assert req.symbol == "AAPL"
        assert req.asset_id is None

    def test_accepts_both_asset_id_and_symbol(self):
        req = SimulationRequest(asset_id=1, symbol="AAPL")
        assert req.asset_id == 1
        assert req.symbol == "AAPL"

    def test_rejects_neither_asset_id_nor_symbol(self):
        with pytest.raises(ValidationError) as exc_info:
            SimulationRequest()
        assert "Provide either asset_id or symbol" in str(exc_info.value)

    def test_default_values(self):
        req = SimulationRequest(symbol="MSFT")
        assert req.timeframe == "1d"
        assert req.num_paths == 1000
        assert req.horizon_steps == 252
        assert req.use_stored_params is True
        assert req.custom_params is None

    def test_num_paths_bounds(self):
        with pytest.raises(ValidationError):
            SimulationRequest(symbol="AAPL", num_paths=50)
        with pytest.raises(ValidationError):
            SimulationRequest(symbol="AAPL", num_paths=100_000)

    def test_horizon_steps_bounds(self):
        with pytest.raises(ValidationError):
            SimulationRequest(symbol="AAPL", horizon_steps=0)
        with pytest.raises(ValidationError):
            SimulationRequest(symbol="AAPL", horizon_steps=9999)


# ---------------------------------------------------------------------------
# _resolve_asset_id helper
# ---------------------------------------------------------------------------

class TestResolveAssetId:
    @pytest.mark.asyncio
    async def test_returns_asset_id_when_provided(self):
        from routes.monte_carlo import _resolve_asset_id

        session = AsyncMock()
        result = await _resolve_asset_id(session, asset_id=42, symbol=None)
        assert result == 42
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolves_symbol_when_no_asset_id(self):
        from routes.monte_carlo import _resolve_asset_id

        session = AsyncMock()
        with patch("routes.monte_carlo.get_asset_id_by_symbol", new=AsyncMock(return_value=7)):
            result = await _resolve_asset_id(session, asset_id=None, symbol="AAPL")
        assert result == 7

    @pytest.mark.asyncio
    async def test_raises_404_when_symbol_not_found(self):
        from routes.monte_carlo import _resolve_asset_id

        session = AsyncMock()
        with patch("routes.monte_carlo.get_asset_id_by_symbol", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc_info:
                await _resolve_asset_id(session, asset_id=None, symbol="FAKE")
        assert exc_info.value.status_code == 404
        assert "FAKE" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_asset_id_takes_priority_over_symbol(self):
        from routes.monte_carlo import _resolve_asset_id

        session = AsyncMock()
        result = await _resolve_asset_id(session, asset_id=5, symbol="IGNORED")
        assert result == 5


# ---------------------------------------------------------------------------
# params_dict serialisation: datetime must not appear in model_dump(mode="json")
# ---------------------------------------------------------------------------

class TestParamsDictSerialization:
    def test_model_dump_json_mode_converts_datetimes(self):
        from dtos.simulation_dto import (
            CalibratedModelParams,
            JumpParams,
            VasicekParams,
        )

        params = CalibratedModelParams(
            vasicek=VasicekParams(k=1.0, theta=100.0, sigma=10.0),
            jumps=JumpParams(
                lambda_up=1.0,
                lambda_down=1.0,
                mu_up=0.01,
                sigma_up=0.005,
                mu_down=-0.01,
                sigma_down=0.005,
            ),
            calibration_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            calibration_end=datetime(2025, 1, 1, tzinfo=timezone.utc),
            num_observations=252,
        )

        result = params.model_dump(mode="json")

        assert isinstance(result["calibration_start"], str)
        assert isinstance(result["calibration_end"], str)
        assert "2024-01-01" in result["calibration_start"]
        assert "2025-01-01" in result["calibration_end"]

    def test_model_dump_default_mode_returns_datetime_objects(self):
        from dtos.simulation_dto import (
            CalibratedModelParams,
            JumpParams,
            VasicekParams,
        )

        params = CalibratedModelParams(
            vasicek=VasicekParams(k=1.0, theta=100.0, sigma=10.0),
            jumps=JumpParams(
                lambda_up=1.0,
                lambda_down=1.0,
                mu_up=0.01,
                sigma_up=0.005,
                mu_down=-0.01,
                sigma_down=0.005,
            ),
            calibration_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            calibration_end=datetime(2025, 1, 1, tzinfo=timezone.utc),
            num_observations=252,
        )

        result = params.model_dump()

        assert isinstance(result["calibration_start"], datetime)
        assert isinstance(result["calibration_end"], datetime)


# ---------------------------------------------------------------------------
# SimulationRequest include_distribution flag
# ---------------------------------------------------------------------------

class TestIncludeDistributionFlag:
    def test_defaults_to_false(self):
        req = SimulationRequest(symbol="AAPL")
        assert req.include_distribution is False

    def test_can_be_set_to_true(self):
        req = SimulationRequest(symbol="AAPL", include_distribution=True)
        assert req.include_distribution is True


# ---------------------------------------------------------------------------
# ReturnDistribution and JumpCI DTOs
# ---------------------------------------------------------------------------

class TestReturnDistributionDTO:
    def test_round_trips(self):
        from dtos.simulation_dto import DistributionPoint, ReturnDistribution

        dist = ReturnDistribution(
            histogram=[DistributionPoint(x=0.0, density=1.0)],
            mr_density=[DistributionPoint(x=0.0, density=2.0)],
            jump_up_density=[DistributionPoint(x=0.1, density=0.5)],
            jump_down_density=[DistributionPoint(x=-0.1, density=0.5)],
        )
        dumped = dist.model_dump()
        assert len(dumped["histogram"]) == 1
        assert dumped["histogram"][0]["x"] == 0.0
        assert dumped["mr_density"][0]["density"] == 2.0


class TestJumpCIDTO:
    def test_round_trips(self):
        from dtos.simulation_dto import JumpCI

        ci = JumpCI(mu_low=-0.1, mu_high=0.1, sigma_low=0.05, sigma_high=0.15)
        dumped = ci.model_dump()
        assert dumped["mu_low"] == -0.1
        assert dumped["sigma_high"] == 0.15

    def test_jump_params_ci_optional(self):
        from dtos.simulation_dto import JumpParams

        params = JumpParams(
            lambda_up=1.0,
            lambda_down=1.0,
            mu_up=0.01,
            sigma_up=0.005,
            mu_down=-0.01,
            sigma_down=0.005,
        )
        assert params.ci_up is None
        assert params.ci_down is None

    def test_jump_params_with_ci(self):
        from dtos.simulation_dto import JumpCI, JumpParams

        params = JumpParams(
            lambda_up=1.0,
            lambda_down=1.0,
            mu_up=0.01,
            sigma_up=0.005,
            mu_down=-0.01,
            sigma_down=0.005,
            ci_up=JumpCI(mu_low=-0.1, mu_high=0.1, sigma_low=0.01, sigma_high=0.05),
        )
        assert params.ci_up is not None
        assert params.ci_up.mu_low == -0.1


# ---------------------------------------------------------------------------
# McSimulationOptimizeRequest DTO validation
# ---------------------------------------------------------------------------

class TestMcSimulationOptimizeRequestDTO:
    def test_accepts_symbol_and_grid(self):
        from dtos.simulation_dto import McSimulationOptimizeRequest

        req = McSimulationOptimizeRequest(
            symbol="AAPL",
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            param_grid={"num_paths": [500, 1000], "calibration_years": [5, 10]},
        )
        assert req.symbol == "AAPL"
        assert req.optimize_metric == "prob_positive_return"

    def test_rejects_invalid_date_order(self):
        from dtos.simulation_dto import McSimulationOptimizeRequest

        with pytest.raises(ValidationError):
            McSimulationOptimizeRequest(
                symbol="AAPL",
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
                param_grid={"num_paths": [500]},
            )

    def test_rejects_positive_drawdown_cap(self):
        from dtos.simulation_dto import McSimulationOptimizeRequest

        with pytest.raises(ValidationError):
            McSimulationOptimizeRequest(
                symbol="AAPL",
                start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                param_grid={"num_paths": [500]},
                max_drawdown_cap=0.25,
            )


# ---------------------------------------------------------------------------
# POST /simulation/optimize route
# ---------------------------------------------------------------------------

class TestOptimizeMcSimulationRoute:
    @pytest.mark.asyncio
    async def test_optimize_happy_path(self):
        from features.quantitative_engine.mc_simulation_optimizer import McSimulationOptimizationResult
        from features.quantitative_engine.monte_carlo import SimulationStats
        from routes.monte_carlo import optimize_mc_simulation
        from dtos.simulation_dto import McSimulationOptimizeRequest

        mock_stats = SimulationStats(
            mean_terminal=1.1, std_terminal=0.05, p5=1.0, p25=1.05, p50=1.1,
            p75=1.15, p95=1.2, prob_positive_return=0.65, mean_max_drawdown=-0.1,
        )
        mock_result = McSimulationOptimizationResult(
            best_params={"num_paths": 1000, "calibration_years": 10},
            best_metric=0.72,
            best_avg_oos_max_drawdown=-0.15,
            all_results=[{
                "params": {"num_paths": 1000, "calibration_years": 10},
                "avg_oos_metric": 0.72,
                "avg_oos_max_drawdown": -0.15,
            }],
            n_splits=5,
        )
        mock_sim = MagicMock(stats=mock_stats, percentile_paths={"50": [1.0, 1.1]})

        session = AsyncMock()
        request = McSimulationOptimizeRequest(
            symbol="AAPL",
            start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            param_grid={"num_paths": [500, 1000], "calibration_years": [10]},
            n_splits=2,
        )
        df = pd.DataFrame({
            "time": pd.date_range("2020-01-01", periods=200, freq="D", tz="UTC"),
            "close": np.linspace(100, 150, 200),
        })

        with (
            patch("routes.monte_carlo._resolve_asset_id", new=AsyncMock(return_value=1)),
            patch("routes.monte_carlo.get_ohlcv", new=AsyncMock(return_value=df)),
            patch("routes.monte_carlo.walk_forward_mc_simulation_optimize", return_value=mock_result),
            patch("routes.monte_carlo.run_best_params_simulation", return_value=mock_sim),
        ):
            resp = await optimize_mc_simulation(request, session)

        assert resp.status == "done"
        assert resp.best_params == {"num_paths": 1000, "calibration_years": 10}
        assert resp.best_run_stats is not None
        assert resp.best_run_stats.prob_positive_return == 0.65

    @pytest.mark.asyncio
    async def test_optimize_insufficient_data_422(self):
        from routes.monte_carlo import optimize_mc_simulation
        from dtos.simulation_dto import McSimulationOptimizeRequest

        session = AsyncMock()
        request = McSimulationOptimizeRequest(
            symbol="AAPL",
            start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            param_grid={"num_paths": [500]},
            n_splits=5,
        )
        df = pd.DataFrame({"time": [], "close": []})

        with (
            patch("routes.monte_carlo._resolve_asset_id", new=AsyncMock(return_value=1)),
            patch("routes.monte_carlo.get_ohlcv", new=AsyncMock(return_value=df)),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await optimize_mc_simulation(request, session)
        assert exc_info.value.status_code == 404
