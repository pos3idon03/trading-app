"""Tests for live trading routes."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestStreamStartEndpoint:
    def test_start_stream_success(self):
        with patch("routes.live_trading.get_stream") as mock_stream:
            mock_status = MagicMock()
            mock_status.connected = True
            mock_status.subscribed_symbols = ["AAPL"]
            mock_status.last_tick_at = None
            mock_status.error = None
            mock_status.reconnect_count = 0
            stream_instance = MagicMock()
            stream_instance.status = mock_status
            stream_instance.start = AsyncMock()
            stream_instance.on_tick = MagicMock()
            mock_stream.return_value = stream_instance

            response = client.post("/api/v1/live/start", json={"symbols": ["AAPL"]})
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert "AAPL" in data["subscribed_symbols"]
            stream_instance.start.assert_awaited_once()

    def test_start_stream_error_propagated(self):
        with patch("routes.live_trading.get_stream") as mock_stream:
            mock_status = MagicMock()
            mock_status.connected = False
            mock_status.subscribed_symbols = ["AAPL"]
            mock_status.last_tick_at = None
            mock_status.error = "'NoneType' object has no attribute 'is_running'"
            mock_status.reconnect_count = 5
            stream_instance = MagicMock()
            stream_instance.status = mock_status
            stream_instance.start = AsyncMock()
            stream_instance.on_tick = MagicMock()
            mock_stream.return_value = stream_instance

            response = client.post("/api/v1/live/start", json={"symbols": ["AAPL"]})
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
            assert data["error"] is not None


class TestStreamStatusEndpoint:
    def test_get_status(self):
        with patch("routes.live_trading.get_stream") as mock_stream:
            mock_status = MagicMock()
            mock_status.connected = False
            mock_status.subscribed_symbols = []
            mock_status.last_tick_at = None
            mock_status.error = None
            mock_status.reconnect_count = 0
            mock_stream.return_value.status = mock_status

            response = client.get("/api/v1/live/status")
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
            assert data["subscribed_symbols"] == []


class TestIndicatorsEndpoint:
    def test_get_indicators_no_data(self):
        with patch("routes.live_trading._get_resampler") as mock_res:
            mock_res.return_value.get_bars.return_value = []

            with patch("routes.live_trading.live_trading_dal") as mock_dal:
                mock_dal.get_latest_indicator = AsyncMock(return_value=None)

                response = client.get("/api/v1/live/indicators/AAPL?timeframe=1h")
                assert response.status_code == 200
                data = response.json()
                assert data["symbol"] == "AAPL"
                assert data["close_price"] == 0.0


class TestSignalEndpoints:
    def test_get_latest_signal_not_found(self):
        with patch("routes.live_trading.live_trading_dal") as mock_dal:
            mock_dal.get_latest_signal = AsyncMock(return_value=None)

            response = client.get("/api/v1/live/signals/AAPL")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data

    def test_get_signal_history_empty(self):
        with patch("routes.live_trading.live_trading_dal") as mock_dal:
            mock_dal.get_signal_history = AsyncMock(return_value=([], 0))

            response = client.get("/api/v1/live/signals?limit=10")
            assert response.status_code == 200
            data = response.json()
            assert data["signals"] == []
            assert data["total"] == 0
