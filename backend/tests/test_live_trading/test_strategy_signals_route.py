"""Tests for GET /live/strategy-signals/{symbol} route."""
import math
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
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
    return [_make_bar(close=100.0 + 5.0 * math.sin(i * 0.3) + i * 0.05) for i in range(n)]


def _make_ohlcv_df(n: int) -> pd.DataFrame:
    """Create a synthetic OHLCV DataFrame matching the DB output shape."""
    rows = []
    for i in range(n):
        close = 100.0 + 5.0 * math.sin(i * 0.3) + i * 0.05
        rows.append({
            "open": close - 0.5, "high": close + 1.0,
            "low": close - 1.0, "close": close, "volume": 1000,
        })
    return pd.DataFrame(rows)


class TestStrategySignalsRoute:
    def test_returns_empty_strategies_when_insufficient_bars_and_no_db(self):
        bars = _make_bars(10)
        with patch("routes.live_trading._get_resampler") as mock_resampler, \
             patch("routes.live_trading._fetch_bars_from_db", new_callable=AsyncMock, return_value=[]):
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
            assert "indicator_value" in s
            assert "indicator_label" in s
            assert "params" in s

    def test_rsi_strategy_returns_indicator_value(self):
        bars = _make_bars(60)
        with patch("routes.live_trading._get_resampler") as mock_resampler:
            mock_resampler.return_value.get_bars.return_value = bars
            response = client.get("/api/v1/live/strategy-signals/AAPL")

        assert response.status_code == 200
        strategies = {s["strategy"]: s for s in response.json()["strategies"]}
        assert "rsi" in strategies
        rsi = strategies["rsi"]
        assert rsi["indicator_label"] == "RSI"
        assert rsi["indicator_value"] is not None
        assert isinstance(rsi["params"], dict)

    def test_symbol_is_uppercased(self):
        bars = _make_bars(5)
        with patch("routes.live_trading._get_resampler") as mock_resampler, \
             patch("routes.live_trading._fetch_bars_from_db", new_callable=AsyncMock, return_value=[]):
            mock_resampler.return_value.get_bars.return_value = bars
            response = client.get("/api/v1/live/strategy-signals/aapl")

        assert response.status_code == 200
        assert response.json()["symbol"] == "AAPL"

    def test_custom_timeframe_query_param(self):
        bars = _make_bars(5)
        with patch("routes.live_trading._get_resampler") as mock_resampler, \
             patch("routes.live_trading._fetch_bars_from_db", new_callable=AsyncMock, return_value=[]):
            mock_resampler.return_value.get_bars.return_value = bars
            response = client.get("/api/v1/live/strategy-signals/AAPL?timeframe=4h")

        assert response.status_code == 200
        assert response.json()["timeframe"] == "4h"
        mock_resampler.return_value.get_bars.assert_called_once_with("AAPL", "4h")


class TestStrategySignalsDbFallback:
    """Tests for DB fallback when resampler has insufficient bars."""

    def test_falls_back_to_db_when_resampler_empty(self):
        db_bars = _make_bars(60)
        with patch("routes.live_trading._get_resampler") as mock_resampler, \
             patch("routes.live_trading._fetch_bars_from_db", new_callable=AsyncMock, return_value=db_bars):
            mock_resampler.return_value.get_bars.return_value = []
            response = client.get("/api/v1/live/strategy-signals/BARC.L?timeframe=1w")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BARC.L"
        assert data["timeframe"] == "1w"
        assert data["bar_count"] == 60
        assert len(data["strategies"]) > 0

    def test_falls_back_to_db_when_resampler_has_few_bars(self):
        resampler_bars = _make_bars(5)
        db_bars = _make_bars(60)
        with patch("routes.live_trading._get_resampler") as mock_resampler, \
             patch("routes.live_trading._fetch_bars_from_db", new_callable=AsyncMock, return_value=db_bars):
            mock_resampler.return_value.get_bars.return_value = resampler_bars
            response = client.get("/api/v1/live/strategy-signals/AAPL?timeframe=1w")

        assert response.status_code == 200
        data = response.json()
        assert data["bar_count"] == 60
        assert len(data["strategies"]) > 0

    def test_db_fallback_returns_empty_when_db_also_insufficient(self):
        db_bars = _make_bars(10)
        with patch("routes.live_trading._get_resampler") as mock_resampler, \
             patch("routes.live_trading._fetch_bars_from_db", new_callable=AsyncMock, return_value=db_bars):
            mock_resampler.return_value.get_bars.return_value = []
            response = client.get("/api/v1/live/strategy-signals/AAPL?timeframe=1w")

        assert response.status_code == 200
        data = response.json()
        assert data["strategies"] == []

    def test_db_fallback_strategies_have_valid_signals(self):
        db_bars = _make_bars(60)
        with patch("routes.live_trading._get_resampler") as mock_resampler, \
             patch("routes.live_trading._fetch_bars_from_db", new_callable=AsyncMock, return_value=db_bars):
            mock_resampler.return_value.get_bars.return_value = []
            response = client.get("/api/v1/live/strategy-signals/AAPL?timeframe=1w")

        assert response.status_code == 200
        for s in response.json()["strategies"]:
            assert s["signal"] in ("BUY", "SELL", "NEUTRAL")
            assert "params" in s

    def test_skips_db_fallback_when_resampler_has_enough_bars(self):
        resampler_bars = _make_bars(60)
        with patch("routes.live_trading._get_resampler") as mock_resampler, \
             patch("routes.live_trading._fetch_bars_from_db", new_callable=AsyncMock) as mock_db:
            mock_resampler.return_value.get_bars.return_value = resampler_bars
            response = client.get("/api/v1/live/strategy-signals/AAPL")

        assert response.status_code == 200
        assert len(response.json()["strategies"]) > 0
        mock_db.assert_not_called()
