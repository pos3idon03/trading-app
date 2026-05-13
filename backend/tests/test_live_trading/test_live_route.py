"""Tests for live trading routes."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestStreamStartEndpoint:
    def test_start_stream_success(self):
        with (
            patch("routes.live_trading.get_stream") as mock_stream,
            patch(
                "routes.live_trading._register_streaming_assets", new=AsyncMock()
            ) as mock_register,
        ):
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
            mock_register.assert_awaited_once()

    def test_start_stream_registers_all_symbols(self):
        with (
            patch("routes.live_trading.get_stream") as mock_stream,
            patch(
                "routes.live_trading._register_streaming_assets", new=AsyncMock()
            ) as mock_register,
        ):
            mock_status = MagicMock()
            mock_status.connected = True
            mock_status.subscribed_symbols = ["AAPL", "MSFT"]
            mock_status.last_tick_at = None
            mock_status.error = None
            mock_status.reconnect_count = 0
            stream_instance = MagicMock()
            stream_instance.status = mock_status
            stream_instance.start = AsyncMock()
            stream_instance.on_tick = MagicMock()
            mock_stream.return_value = stream_instance

            response = client.post(
                "/api/v1/live/start", json={"symbols": ["AAPL", "MSFT"]}
            )
            assert response.status_code == 200
            _, call_kwargs = mock_register.call_args
            assert set(call_kwargs.get("symbols", mock_register.call_args[0][1])) == {
                "AAPL",
                "MSFT",
            }

    def test_start_stream_returns_connected_true_after_poll(self):
        """start_stream must wait for the WS task to set connected=True."""
        call_count = 0

        class _LazyStatus:
            subscribed_symbols = ["AAPL"]
            last_tick_at = None
            error = None
            reconnect_count = 0

            @property
            def connected(self):
                nonlocal call_count
                call_count += 1
                return call_count >= 3  # False for first 2 polls, True on 3rd

        with (
            patch("routes.live_trading.get_stream") as mock_stream,
            patch("routes.live_trading._register_streaming_assets", new=AsyncMock()),
        ):
            lazy_status = _LazyStatus()
            stream_instance = MagicMock()
            stream_instance.status = lazy_status
            stream_instance.start = AsyncMock()
            stream_instance.on_tick = MagicMock()
            mock_stream.return_value = stream_instance

            response = client.post("/api/v1/live/start", json={"symbols": ["AAPL"]})
            assert response.status_code == 200
            assert response.json()["connected"] is True

    def test_start_stream_error_propagated(self):
        with (
            patch("routes.live_trading.get_stream") as mock_stream,
            patch(
                "routes.live_trading._register_streaming_assets", new=AsyncMock()
            ),
        ):
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
        with (
            patch("routes.live_trading._get_resampler") as mock_res,
            patch("routes.live_trading.live_trading_dal") as mock_dal,
            patch(
                "routes.live_trading.get_asset_id_by_symbol",
                new=AsyncMock(return_value=1),
            ),
        ):
            mock_res.return_value.get_bars.return_value = []
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
