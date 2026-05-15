"""Tests for backtest DTO validation, symbol resolution, and simulated-data path."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from dtos.backtest_dto import BacktestRequest


# ---------------------------------------------------------------------------
# BacktestRequest DTO validation
# ---------------------------------------------------------------------------

class TestBacktestRequestDTO:
    def _base_kwargs(self) -> dict:
        return {
            "strategy_name": "ma_crossover",
            "start_date": datetime(2022, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
        }

    def test_accepts_asset_id_only(self):
        req = BacktestRequest(asset_id=1, **self._base_kwargs())
        assert req.asset_id == 1
        assert req.symbol is None

    def test_accepts_symbol_only(self):
        req = BacktestRequest(symbol="AAPL", **self._base_kwargs())
        assert req.symbol == "AAPL"
        assert req.asset_id is None

    def test_accepts_both_asset_id_and_symbol(self):
        req = BacktestRequest(asset_id=1, symbol="AAPL", **self._base_kwargs())
        assert req.asset_id == 1
        assert req.symbol == "AAPL"

    def test_accepts_simulation_id_without_asset_or_symbol(self):
        req = BacktestRequest(simulation_id=7, **self._base_kwargs())
        assert req.simulation_id == 7
        assert req.asset_id is None
        assert req.symbol is None

    def test_rejects_neither_asset_id_nor_symbol_nor_simulation_id(self):
        with pytest.raises(ValidationError) as exc_info:
            BacktestRequest(**self._base_kwargs())
        assert "Provide either asset_id, symbol, or simulation_id" in str(exc_info.value)

    def test_default_initial_capital(self):
        req = BacktestRequest(symbol="MSFT", **self._base_kwargs())
        assert req.initial_capital == 100_000.0

    def test_initial_capital_minimum(self):
        with pytest.raises(ValidationError):
            BacktestRequest(symbol="AAPL", initial_capital=500.0, **self._base_kwargs())


# ---------------------------------------------------------------------------
# _resolve_asset_id helper in backtest route
# ---------------------------------------------------------------------------

class TestBacktestResolveAssetId:
    @pytest.mark.asyncio
    async def test_returns_asset_id_when_provided(self):
        from routes.backtest import _resolve_asset_id

        session = AsyncMock()
        result = await _resolve_asset_id(session, asset_id=10, symbol=None)
        assert result == 10

    @pytest.mark.asyncio
    async def test_resolves_symbol_when_no_asset_id(self):
        from routes.backtest import _resolve_asset_id

        session = AsyncMock()
        with patch("routes.backtest.get_asset_id_by_symbol", new=AsyncMock(return_value=3)):
            result = await _resolve_asset_id(session, asset_id=None, symbol="SPY")
        assert result == 3

    @pytest.mark.asyncio
    async def test_raises_404_when_symbol_not_found(self):
        from routes.backtest import _resolve_asset_id

        session = AsyncMock()
        with patch("routes.backtest.get_asset_id_by_symbol", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc_info:
                await _resolve_asset_id(session, asset_id=None, symbol="NOPE")
        assert exc_info.value.status_code == 404
        assert "NOPE" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_asset_id_takes_priority_over_symbol(self):
        from routes.backtest import _resolve_asset_id

        session = AsyncMock()
        result = await _resolve_asset_id(session, asset_id=99, symbol="IGNORED")
        assert result == 99


# ---------------------------------------------------------------------------
# prepare_simulated_dataframe
# ---------------------------------------------------------------------------


class TestPrepareSimulatedDataframe:
    def _make_sim_record(self, has_paths: bool = True):
        rec = MagicMock()
        rec.s0 = 100.0
        rec.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        if has_paths:
            rec.percentile_paths = {"p50": [1.0, 1.02, 0.98, 1.05, 1.03]}
        else:
            rec.percentile_paths = None
        return rec

    def test_returns_dataframe_with_correct_shape(self):
        from features.backtesting.runner import prepare_simulated_dataframe

        rec = self._make_sim_record()
        df = prepare_simulated_dataframe(rec)
        assert len(df) == 5
        assert "close" in df.columns
        assert "time" in df.columns

    def test_prices_scaled_by_s0(self):
        from features.backtesting.runner import prepare_simulated_dataframe

        rec = self._make_sim_record()
        df = prepare_simulated_dataframe(rec)
        assert df["close"].iloc[0] == pytest.approx(100.0 * 1.0)
        assert df["close"].iloc[1] == pytest.approx(100.0 * 1.02)

    def test_raises_when_no_paths(self):
        from features.backtesting.runner import prepare_simulated_dataframe

        rec = self._make_sim_record(has_paths=False)
        with pytest.raises(ValueError, match="no percentile_paths"):
            prepare_simulated_dataframe(rec)

    def test_falls_back_to_first_path_key_if_no_p50(self):
        from features.backtesting.runner import prepare_simulated_dataframe

        rec = MagicMock()
        rec.s0 = 50.0
        rec.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        rec.percentile_paths = {"p25": [1.0, 0.95, 0.90]}
        df = prepare_simulated_dataframe(rec)
        assert len(df) == 3
        assert df["close"].iloc[0] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Simulated-data backtest route path
# ---------------------------------------------------------------------------


class TestSimulatedBacktestRoute:
    def _make_sim_record(self):
        rec = MagicMock()
        rec.asset_id = 3
        rec.s0 = 100.0
        rec.status = "done"
        rec.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        rec.percentile_paths = {"p50": list(np.linspace(1.0, 1.2, 50))}
        return rec

    def _make_backtest_result(self):
        from features.backtesting.runner import BacktestResult
        return BacktestResult(
            metrics={
                "sharpe_ratio": 1.2, "sortino_ratio": 1.5, "max_drawdown": -0.10,
                "win_rate": 0.55, "profit_factor": 1.3, "total_return": 0.20,
                "annualized_return": 0.12, "num_trades": 10,
            },
            equity_curve=[{"time": "2024-01-01", "value": 100000}],
            trade_log=[],
            buy_hold_curve=[{"time": "2024-01-01", "value": 100000}],
            indicator_series=[],
            duration_ms=50.0,
        )

    @pytest.mark.asyncio
    async def test_runs_backtest_on_simulated_data(self):
        from routes.backtest import execute_backtest

        req = BacktestRequest(
            simulation_id=7,
            strategy_name="ma_crossover",
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
            strategy_params={"fast_window": 5, "slow_window": 20},
        )
        session = AsyncMock()

        with (
            patch("routes.backtest.get_simulation", new=AsyncMock(return_value=self._make_sim_record())),
            patch("routes.backtest.run_backtest", return_value=self._make_backtest_result()),
        ):
            response = await execute_backtest(req, session)

        assert response.status == "done"
        assert response.asset_id == 3
        assert response.backtest_id is None

    @pytest.mark.asyncio
    async def test_simulation_not_found_raises_404(self):
        from routes.backtest import execute_backtest

        req = BacktestRequest(
            simulation_id=999,
            strategy_name="ma_crossover",
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )
        session = AsyncMock()

        with patch("routes.backtest.get_simulation", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc_info:
                await execute_backtest(req, session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_simulation_not_done_raises_422(self):
        from routes.backtest import execute_backtest

        pending_sim = self._make_sim_record()
        pending_sim.status = "running"
        req = BacktestRequest(
            simulation_id=7,
            strategy_name="ma_crossover",
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )
        session = AsyncMock()

        with patch("routes.backtest.get_simulation", new=AsyncMock(return_value=pending_sim)):
            with pytest.raises(HTTPException) as exc_info:
                await execute_backtest(req, session)
        assert exc_info.value.status_code == 422
