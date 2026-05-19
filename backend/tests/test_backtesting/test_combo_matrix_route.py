"""Tests for POST /backtest/combo-matrix route."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from dtos.backtest_dto import ComboMatrixRequest, ComboMatrixResponse
from features.backtesting.combo_matrix_runner import ComboMatrixResult


def _base_kwargs() -> dict:
    return {
        "symbol": "AAPL",
        "strategies": ["ma_crossover", "rsi"],
        "start_date": datetime(2022, 1, 1, tzinfo=timezone.utc),
        "end_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
    }


class TestComboMatrixRequestDTO:
    def test_accepts_valid_request(self):
        req = ComboMatrixRequest(**_base_kwargs())
        assert req.metric == "sharpe_ratio"
        assert req.combination_mode == "majority"

    def test_rejects_single_strategy(self):
        with pytest.raises(ValidationError):
            ComboMatrixRequest(
                symbol="AAPL",
                strategies=["ma_crossover"],
                start_date=datetime(2022, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            )

    def test_rejects_unknown_strategy(self):
        kwargs = _base_kwargs()
        kwargs["strategies"] = ["ma_crossover", "not_a_strategy"]
        with pytest.raises(ValidationError):
            ComboMatrixRequest(**kwargs)

    def test_rejects_duplicate_strategies(self):
        kwargs = _base_kwargs()
        kwargs["strategies"] = ["ma_crossover", "ma_crossover"]
        with pytest.raises(ValidationError):
            ComboMatrixRequest(**kwargs)

    def test_rejects_missing_asset_and_symbol(self):
        with pytest.raises(ValidationError):
            ComboMatrixRequest(
                strategies=["ma_crossover", "rsi"],
                start_date=datetime(2022, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            )


@pytest.fixture
def ohlcv_df():
    rng = np.random.default_rng(7)
    n = 120
    close = pd.Series(50.0 * np.cumprod(1 + rng.normal(0.001, 0.01, n)))
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "time": dates,
        "open": close.values,
        "high": close.values,
        "low": close.values,
        "close": close.values,
        "volume": 1_000.0,
    })


class TestExecuteComboMatrixRoute:
    @pytest.mark.asyncio
    async def test_returns_matrix_response(self, ohlcv_df):
        from routes.backtest import execute_combo_matrix

        request = ComboMatrixRequest(**_base_kwargs())
        session = AsyncMock()
        mock_result = ComboMatrixResult(
            strategies=["ma_crossover", "rsi"],
            metric="sharpe_ratio",
            combination_mode="majority",
            values=[[1.0, 0.5], [0.5, 1.2]],
            duration_ms=100.0,
        )

        with (
            patch("routes.backtest._resolve_asset_id", new=AsyncMock(return_value=1)),
            patch(
                "routes.backtest._load_combo_matrix_ohlcv",
                new=AsyncMock(return_value=(ohlcv_df, request.start_date)),
            ),
            patch("routes.backtest.run_combo_matrix", return_value=mock_result),
        ):
            response = await execute_combo_matrix(request, session)

        assert isinstance(response, ComboMatrixResponse)
        assert response.asset_id == 1
        assert len(response.values) == 2
        assert response.values[0][1] == 0.5

    @pytest.mark.asyncio
    async def test_404_when_no_data(self):
        from routes.backtest import execute_combo_matrix

        request = ComboMatrixRequest(**_base_kwargs())
        session = AsyncMock()
        empty_df = pd.DataFrame()

        with (
            patch("routes.backtest._resolve_asset_id", new=AsyncMock(return_value=1)),
            patch(
                "routes.backtest._load_combo_matrix_ohlcv",
                new=AsyncMock(return_value=(empty_df, request.start_date)),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await execute_combo_matrix(request, session)
        assert exc_info.value.status_code == 404
