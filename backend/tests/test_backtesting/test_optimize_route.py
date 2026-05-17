"""Tests for the POST /api/v1/backtest/optimize route."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from dtos.backtest_dto import OptimizationRequest


# ---------------------------------------------------------------------------
# OptimizationRequest DTO validation
# ---------------------------------------------------------------------------


class TestOptimizationRequestDTO:
    def _base_kwargs(self) -> dict:
        return {
            "strategy_name": "ma_crossover",
            "start_date": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "param_grid": {"fast_window": [5, 10], "slow_window": [20, 50]},
        }

    def test_accepts_symbol(self):
        req = OptimizationRequest(symbol="AAPL", **self._base_kwargs())
        assert req.symbol == "AAPL"

    def test_accepts_asset_id(self):
        req = OptimizationRequest(asset_id=1, **self._base_kwargs())
        assert req.asset_id == 1

    def test_rejects_neither_asset_id_nor_symbol(self):
        with pytest.raises(ValidationError) as exc_info:
            OptimizationRequest(**self._base_kwargs())
        assert "Provide either asset_id or symbol" in str(exc_info.value)

    def test_defaults(self):
        req = OptimizationRequest(symbol="SPY", **self._base_kwargs())
        assert req.n_splits == 5
        assert req.optimize_metric == "sharpe_ratio"
        assert req.initial_capital == 100_000.0

    def test_custom_n_splits(self):
        req = OptimizationRequest(symbol="SPY", n_splits=3, **self._base_kwargs())
        assert req.n_splits == 3

    def test_n_splits_out_of_range(self):
        with pytest.raises(ValidationError):
            OptimizationRequest(symbol="SPY", n_splits=1, **self._base_kwargs())

    def test_n_splits_max(self):
        with pytest.raises(ValidationError):
            OptimizationRequest(symbol="SPY", n_splits=21, **self._base_kwargs())

    def test_accepts_max_drawdown_cap(self):
        req = OptimizationRequest(
            symbol="SPY", max_drawdown_cap=-0.25, **self._base_kwargs()
        )
        assert req.max_drawdown_cap == -0.25

    def test_rejects_positive_max_drawdown_cap(self):
        with pytest.raises(ValidationError):
            OptimizationRequest(symbol="SPY", max_drawdown_cap=0.1, **self._base_kwargs())


# ---------------------------------------------------------------------------
# Route: _resolve_asset_id (shared helper, imported from backtest route)
# ---------------------------------------------------------------------------


class TestOptimizationRouteResolveAsset:
    @pytest.mark.asyncio
    async def test_asset_id_returns_directly(self):
        from routes.backtest import _resolve_asset_id

        session = AsyncMock()
        result = await _resolve_asset_id(session, asset_id=5, symbol=None)
        assert result == 5

    @pytest.mark.asyncio
    async def test_symbol_resolution(self):
        from routes.backtest import _resolve_asset_id

        session = AsyncMock()
        with patch("routes.backtest.get_asset_id_by_symbol", new=AsyncMock(return_value=7)):
            result = await _resolve_asset_id(session, asset_id=None, symbol="MSFT")
        assert result == 7

    @pytest.mark.asyncio
    async def test_symbol_not_found_raises_404(self):
        from routes.backtest import _resolve_asset_id

        session = AsyncMock()
        with patch("routes.backtest.get_asset_id_by_symbol", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc_info:
                await _resolve_asset_id(session, asset_id=None, symbol="UNKNOWN")
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Route: run_optimization — stateless, no DB writes
# ---------------------------------------------------------------------------


class TestRunOptimizationRoute:
    def _make_df(self):
        import numpy as np
        import pandas as pd

        rng = np.random.default_rng(0)
        prices = 100 + np.cumsum(rng.normal(0, 1, 400))
        dates = pd.date_range("2020-01-01", periods=400, freq="D")
        return pd.DataFrame({"time": dates, "close": prices})

    @pytest.mark.asyncio
    async def test_successful_optimization(self):
        from features.backtesting.optimizer import OptimizationResult
        from features.backtesting.runner import BacktestResult
        from routes.backtest import run_optimization

        mock_result = OptimizationResult(
            best_params={"fast_window": 10, "slow_window": 50},
            best_sharpe=0.9,
            best_avg_oos_max_drawdown=-0.12,
            all_results=[
                {
                    "params": {"fast_window": 10, "slow_window": 50},
                    "avg_oos_metric": 0.9,
                    "avg_oos_max_drawdown": -0.12,
                },
                {
                    "params": {"fast_window": 5, "slow_window": 20},
                    "avg_oos_metric": 0.4,
                    "avg_oos_max_drawdown": -0.30,
                },
            ],
            n_splits=2,
        )
        mock_bt = BacktestResult(
            metrics={
                "sharpe_ratio": 0.493,
                "sortino_ratio": 0.493,
                "max_drawdown": -0.202,
                "win_rate": 0.41,
                "profit_factor": 1.53,
                "total_return": 0.3878,
                "annualized_return": 0.12,
                "num_trades": 39,
            },
            equity_curve=[],
            trade_log=[],
            buy_hold_curve=[],
            indicator_series=[],
            duration_ms=35.0,
        )

        req = OptimizationRequest(
            symbol="AAPL",
            strategy_name="ma_crossover",
            start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            param_grid={"fast_window": [5, 10], "slow_window": [20, 50]},
            n_splits=2,
        )
        session = AsyncMock()

        with (
            patch("routes.backtest.get_asset_id_by_symbol", new=AsyncMock(return_value=1)),
            patch("routes.backtest.load_ohlcv_with_warmup", new=AsyncMock(return_value=self._make_df())),
            patch("routes.backtest.walk_forward_optimize", return_value=mock_result),
            patch("routes.backtest.run_backtest", return_value=mock_bt),
        ):
            response = await run_optimization(req, session)

        assert response.optimization_id is None
        assert response.status == "done"
        assert response.best_params == {"fast_window": 10, "slow_window": 50}
        assert response.best_metric == pytest.approx(0.9)
        assert response.best_avg_oos_max_drawdown == pytest.approx(-0.12)
        assert len(response.all_results) == 2
        assert response.full_period_metrics is not None
        assert response.full_period_metrics.sortino_ratio == pytest.approx(0.493)
        assert response.full_period_metrics.max_drawdown == pytest.approx(-0.202)
        assert response.full_period_metrics.num_trades == 39

    @pytest.mark.asyncio
    async def test_full_period_backtest_failure_returns_none(self):
        from features.backtesting.optimizer import OptimizationResult
        from routes.backtest import run_optimization

        mock_result = OptimizationResult(
            best_params={"fast_window": 10},
            best_sharpe=0.9,
            best_avg_oos_max_drawdown=-0.12,
            all_results=[],
            n_splits=2,
        )
        req = OptimizationRequest(
            symbol="AAPL",
            strategy_name="ma_crossover",
            start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            param_grid={"fast_window": [5, 10]},
            n_splits=2,
        )
        session = AsyncMock()

        with (
            patch("routes.backtest.get_asset_id_by_symbol", new=AsyncMock(return_value=1)),
            patch("routes.backtest.load_ohlcv_with_warmup", new=AsyncMock(return_value=self._make_df())),
            patch("routes.backtest.walk_forward_optimize", return_value=mock_result),
            patch("routes.backtest.run_backtest", side_effect=RuntimeError("boom")),
        ):
            response = await run_optimization(req, session)

        assert response.status == "done"
        assert response.full_period_metrics is None

    @pytest.mark.asyncio
    async def test_no_feasible_combo_raises_422(self):
        from features.backtesting.optimizer import NO_FEASIBLE_MSG
        from routes.backtest import run_optimization

        req = OptimizationRequest(
            symbol="AAPL",
            strategy_name="ma_crossover",
            start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            param_grid={"fast_window": [5, 10]},
            n_splits=2,
            max_drawdown_cap=-0.10,
        )
        session = AsyncMock()

        with (
            patch("routes.backtest.get_asset_id_by_symbol", new=AsyncMock(return_value=1)),
            patch("routes.backtest.load_ohlcv_with_warmup", new=AsyncMock(return_value=self._make_df())),
            patch(
                "routes.backtest.walk_forward_optimize",
                side_effect=ValueError(NO_FEASIBLE_MSG),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await run_optimization(req, session)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_no_data_raises_404(self):
        import pandas as pd
        from routes.backtest import run_optimization

        req = OptimizationRequest(
            symbol="AAPL",
            strategy_name="ma_crossover",
            start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            param_grid={"fast_window": [5, 10]},
            n_splits=5,
        )
        session = AsyncMock()

        with (
            patch("routes.backtest.get_asset_id_by_symbol", new=AsyncMock(return_value=1)),
            patch("routes.backtest.load_ohlcv_with_warmup", new=AsyncMock(return_value=pd.DataFrame())),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await run_optimization(req, session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_insufficient_rows_raises_422(self):
        import numpy as np
        import pandas as pd
        from routes.backtest import run_optimization

        req = OptimizationRequest(
            symbol="AAPL",
            strategy_name="ma_crossover",
            start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            param_grid={"fast_window": [5, 10]},
            n_splits=5,
        )
        session = AsyncMock()

        # n_splits=5 requires (5+1)*30=180 rows; provide only 10
        small_df = pd.DataFrame({"time": pd.date_range("2022-01-01", periods=10), "close": np.ones(10)})

        with (
            patch("routes.backtest.get_asset_id_by_symbol", new=AsyncMock(return_value=1)),
            patch("routes.backtest.load_ohlcv_with_warmup", new=AsyncMock(return_value=small_df)),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await run_optimization(req, session)
        assert exc_info.value.status_code == 422
