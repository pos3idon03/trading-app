"""Tests for GET /live/strategy-signals/{symbol} route."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _make_bar(close: float = 100.0):
    bar = MagicMock()
    bar.open = close - 0.5
    bar.high = close + 0.5
    bar.low = close - 1.0
    bar.close = close
    bar.volume = 1000
    return bar


def _make_bars(n: int):
    return [_make_bar(close=100.0 + i * 0.1) for i in range(n)]


class TestStrategySignalsRoute:
    def test_returns_empty_strategies_when_insufficient_bars(self):
        bars = _make_bars(10)
        with patch("routes.live_trading._get_resampler") as mock_resampler:
            mock_resampler.return_value.get_bars.return_value = bars
            response = client.get("/api/v1/live/strategy-signals/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["timeframe"] == "1h"
        assert data["bar_count"] == 10
        assert data["strategies"] == []

    def test_returns_strategy_list_when_enough_bars(self):
        bars = _make_bars(60)
        with patch("routes.live_trading._get_resampler") as mock_resampler:
            mock_resampler.return_value.get_bars.return_value = bars
            response = client.get("/api/v1/live/strategy-signals/MSFT")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "MSFT"
        assert data["bar_count"] == 60
        assert len(data["strategies"]) > 0

    def test_each_strategy_has_required_fields(self):
        bars = _make_bars(60)
        with patch("routes.live_trading._get_resampler") as mock_resampler:
            mock_resampler.return_value.get_bars.return_value = bars
            response = client.get("/api/v1/live/strategy-signals/AAPL")

        assert response.status_code == 200
        for s in response.json()["strategies"]:
            assert "strategy" in s
            assert "label" in s
            assert "group" in s
            assert s["signal"] in ("BUY", "SELL", "NEUTRAL")

    def test_symbol_is_uppercased(self):
        bars = _make_bars(5)
        with patch("routes.live_trading._get_resampler") as mock_resampler:
            mock_resampler.return_value.get_bars.return_value = bars
            response = client.get("/api/v1/live/strategy-signals/aapl")

        assert response.status_code == 200
        assert response.json()["symbol"] == "AAPL"

    def test_custom_timeframe_query_param(self):
        bars = _make_bars(5)
        with patch("routes.live_trading._get_resampler") as mock_resampler:
            mock_resampler.return_value.get_bars.return_value = bars
            response = client.get("/api/v1/live/strategy-signals/AAPL?timeframe=4h")

        assert response.status_code == 200
        assert response.json()["timeframe"] == "4h"
        mock_resampler.return_value.get_bars.assert_called_once_with("AAPL", "4h")
