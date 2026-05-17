"""Tests for GET /backtest/catalog and POST /backtest/chart-overlay."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from dtos.backtest_dto import ChartOverlayRequest, VALID_STRATEGIES


# ---------------------------------------------------------------------------
# ChartOverlayRequest DTO
# ---------------------------------------------------------------------------

class TestChartOverlayRequestDTO:
    def _base(self) -> dict:
        return {
            "symbol": "AAPL",
            "strategy_name": "rsi",
            "start_date": datetime(2022, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
        }

    def test_accepts_symbol(self):
        req = ChartOverlayRequest(**self._base())
        assert req.symbol == "AAPL"

    def test_accepts_asset_id(self):
        kw = self._base()
        kw.pop("symbol")
        req = ChartOverlayRequest(asset_id=1, **kw)
        assert req.asset_id == 1

    def test_requires_asset_or_symbol(self):
        kw = self._base()
        kw.pop("symbol")
        with pytest.raises(ValidationError, match="Provide either asset_id or symbol"):
            ChartOverlayRequest(**kw)

    def test_rejects_unknown_strategy(self):
        with pytest.raises(ValidationError, match="Unknown strategy"):
            ChartOverlayRequest(**{**self._base(), "strategy_name": "not_a_real_one"})

    def test_default_params_is_empty_dict(self):
        req = ChartOverlayRequest(**self._base())
        assert req.strategy_params == {}


# ---------------------------------------------------------------------------
# Catalog route
# ---------------------------------------------------------------------------

class TestCatalogRoute:
    @pytest.mark.asyncio
    async def test_returns_sorted_list(self):
        from routes.backtest import get_strategy_catalog

        result = await get_strategy_catalog()
        assert isinstance(result, list)
        assert result == sorted(result)
        assert set(result) == VALID_STRATEGIES


# ---------------------------------------------------------------------------
# Chart overlay route
# ---------------------------------------------------------------------------

def _make_df(n: int = 50) -> pd.DataFrame:
    import numpy as np

    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    close = 100 + np.random.randn(n).cumsum()
    return pd.DataFrame({
        "time": dates,
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": 100_000,
    })


class TestChartOverlayRoute:
    def _request_body(self, strategy: str = "rsi") -> dict:
        return {
            "symbol": "AAPL",
            "strategy_name": strategy,
            "timeframe": "1d",
            "start_date": datetime(2022, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
        }

    @pytest.mark.asyncio
    async def test_happy_path_returns_overlay(self):
        from routes.backtest import compute_overlay

        df = _make_df(60)
        mock_session = AsyncMock()
        request = ChartOverlayRequest(**self._request_body())

        with (
            patch("routes.backtest.resolve_asset_id", new=AsyncMock(return_value=1)),
            patch(
                "routes.backtest.load_ohlcv_for_overlay",
                new=AsyncMock(return_value=(df, request.start_date)),
            ),
            patch(
                "routes.backtest.compute_chart_overlay",
                return_value={
                    "strategy_name": "rsi",
                    "trade_log": [],
                    "indicator_series": [{"time": "2022-01-01", "rsi": 55.0}],
                    "duration_ms": 42,
                },
            ),
        ):
            resp = await compute_overlay(request, session=mock_session)

        assert resp.strategy_name == "rsi"
        assert resp.duration_ms == 42

    @pytest.mark.asyncio
    async def test_raises_404_when_asset_not_found(self):
        from routes.backtest import compute_overlay

        mock_session = AsyncMock()
        request = ChartOverlayRequest(**self._request_body())

        with (
            patch("routes.backtest.resolve_asset_id", new=AsyncMock(return_value=None)),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await compute_overlay(request, session=mock_session)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_when_no_ohlcv_data(self):
        from routes.backtest import compute_overlay

        mock_session = AsyncMock()
        request = ChartOverlayRequest(**self._request_body())

        with (
            patch("routes.backtest.resolve_asset_id", new=AsyncMock(return_value=1)),
            patch(
                "routes.backtest.load_ohlcv_for_overlay",
                new=AsyncMock(return_value=(pd.DataFrame(), request.start_date)),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await compute_overlay(request, session=mock_session)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_422_when_too_few_bars(self):
        from routes.backtest import compute_overlay

        mock_session = AsyncMock()
        request = ChartOverlayRequest(**self._request_body())

        with (
            patch("routes.backtest.resolve_asset_id", new=AsyncMock(return_value=1)),
            patch(
                "routes.backtest.load_ohlcv_for_overlay",
                new=AsyncMock(return_value=(_make_df(5), request.start_date)),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await compute_overlay(request, session=mock_session)

        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# load_ohlcv_for_overlay resample fallback
# ---------------------------------------------------------------------------

class TestLoadOhlcvForOverlayResample:
    @pytest.mark.asyncio
    async def test_falls_back_to_resample_when_direct_query_empty(self):
        from features.backtesting.chart_overlay import load_ohlcv_for_overlay

        resampled_df = _make_df(30)
        session = AsyncMock()

        start = datetime(2022, 1, 1, tzinfo=timezone.utc)
        end = datetime(2023, 1, 1, tzinfo=timezone.utc)
        with (
            patch("features.backtesting.chart_overlay.get_ohlcv", new=AsyncMock(return_value=pd.DataFrame())),
            patch("features.backtesting.chart_overlay.resample_ohlcv", new=AsyncMock(return_value=resampled_df)),
        ):
            result, _ = await load_ohlcv_for_overlay(
                session, asset_id=1, timeframe="15m", start=start, end=end
            )

        assert len(result) == 30

    @pytest.mark.asyncio
    async def test_returns_direct_data_when_available(self):
        from features.backtesting.chart_overlay import load_ohlcv_for_overlay

        direct_df = _make_df(50)
        session = AsyncMock()

        start = datetime(2022, 1, 1, tzinfo=timezone.utc)
        end = datetime(2023, 1, 1, tzinfo=timezone.utc)
        with (
            patch("features.backtesting.chart_overlay.get_ohlcv", new=AsyncMock(return_value=direct_df)),
            patch("features.backtesting.chart_overlay.resample_ohlcv", new=AsyncMock()) as mock_resample,
        ):
            result, _ = await load_ohlcv_for_overlay(
                session, asset_id=1, timeframe="1d", start=start, end=end
            )

        mock_resample.assert_not_called()
        assert len(result) == 50

    @pytest.mark.asyncio
    async def test_returns_empty_when_both_paths_empty(self):
        from features.backtesting.chart_overlay import load_ohlcv_for_overlay

        session = AsyncMock()

        start = datetime(2022, 1, 1, tzinfo=timezone.utc)
        end = datetime(2023, 1, 1, tzinfo=timezone.utc)
        with (
            patch("features.backtesting.chart_overlay.get_ohlcv", new=AsyncMock(return_value=pd.DataFrame())),
            patch("features.backtesting.chart_overlay.resample_ohlcv", new=AsyncMock(return_value=pd.DataFrame())),
        ):
            result, _ = await load_ohlcv_for_overlay(
                session, asset_id=1, timeframe="15m", start=start, end=end
            )

        assert result.empty
