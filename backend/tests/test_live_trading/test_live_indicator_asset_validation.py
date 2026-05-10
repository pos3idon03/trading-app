"""Tests verifying that the live indicator endpoint validates asset existence."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /indicators/{symbol}: requires asset to be registered
# ---------------------------------------------------------------------------

class TestIndicatorsAssetValidation:
    def test_unknown_asset_returns_404(self):
        with (
            patch("routes.live_trading.get_asset_id_by_symbol", new=AsyncMock(return_value=None)),
            patch("routes.live_trading.get_db"),
        ):
            response = client.get("/api/v1/live/indicators/FAKE?timeframe=1h")

        assert response.status_code == 404
        assert "not registered" in response.json()["detail"].lower()

    def test_known_asset_with_no_bars_returns_empty_snapshot(self):
        with (
            patch("routes.live_trading.get_asset_id_by_symbol", new=AsyncMock(return_value=1)),
            patch("routes.live_trading._get_resampler") as mock_res,
            patch("routes.live_trading.live_trading_dal") as mock_dal,
            patch("routes.live_trading.get_db"),
        ):
            mock_res.return_value.get_bars.return_value = []
            mock_dal.get_latest_indicator = AsyncMock(return_value=None)

            response = client.get("/api/v1/live/indicators/AAPL?timeframe=1h")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["asset_id"] == 1
        assert data["close_price"] == 0.0

    def test_symbol_is_uppercased_for_lookup(self):
        looked_up = {}

        async def capture_lookup(session, symbol):
            looked_up["symbol"] = symbol
            return None

        with (
            patch("routes.live_trading.get_asset_id_by_symbol", side_effect=capture_lookup),
            patch("routes.live_trading.get_db"),
        ):
            client.get("/api/v1/live/indicators/aapl?timeframe=1h")

        assert looked_up.get("symbol") == "AAPL"

    def test_stored_indicator_includes_asset_id(self):
        mock_stored = MagicMock()
        mock_stored.asset_id = 5
        mock_stored.symbol = "MSFT"
        mock_stored.timeframe = "1h"
        mock_stored.close_price = 420.0
        mock_stored.rsi = 55.0
        mock_stored.macd = None
        mock_stored.macd_signal = None
        mock_stored.macd_histogram = None
        mock_stored.bb_upper = None
        mock_stored.bb_middle = None
        mock_stored.bb_lower = None
        mock_stored.vwap = None
        mock_stored.created_at = None

        with (
            patch("routes.live_trading.get_asset_id_by_symbol", new=AsyncMock(return_value=5)),
            patch("routes.live_trading._get_resampler") as mock_res,
            patch("routes.live_trading.live_trading_dal") as mock_dal,
            patch("routes.live_trading.get_db"),
        ):
            mock_res.return_value.get_bars.return_value = []
            mock_dal.get_latest_indicator = AsyncMock(return_value=mock_stored)

            response = client.get("/api/v1/live/indicators/MSFT?timeframe=1h")

        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == 5
