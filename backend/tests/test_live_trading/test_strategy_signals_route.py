"""Tests for GET /live/strategy-signals/{symbol} route."""
import math
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _make_bar(close: float = 100.0):
    from unittest.mock import MagicMock

    bar = MagicMock()
    bar.open = close - 0.5
    bar.high = close + 0.5
    bar.low = close - 1.0
    bar.close = close
    bar.volume = 1000
    bar.bar_start = "2026-05-18T12:00:00+00:00"
    return bar


def _make_bars(n: int):
    return [_make_bar(close=100.0 + 5.0 * math.sin(i * 0.3) + i * 0.05) for i in range(n)]


class TestStrategySignalsRoute:
    def test_returns_empty_strategies_when_insufficient_bars(self):
        bars = _make_bars(10)
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
            response = client.get("/api/v1/live/strategy-signals/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["timeframe"] == "1h"
        assert data["bar_count"] == 10
        assert data["strategies"] == []

    def test_returns_strategy_list_when_enough_bars(self):
        bars = _make_bars(60)
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
            response = client.get("/api/v1/live/strategy-signals/MSFT")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "MSFT"
        assert data["bar_count"] == 60
        assert len(data["strategies"]) > 0

    def test_each_strategy_has_required_fields(self):
        bars = _make_bars(60)
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
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
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
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
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
            response = client.get("/api/v1/live/strategy-signals/aapl")

        assert response.status_code == 200
        assert response.json()["symbol"] == "AAPL"

    def test_custom_timeframe_query_param(self):
        bars = _make_bars(5)
        mock_resolve = AsyncMock(return_value=bars)
        with patch("routes.live_trading.resolve_bars", new=mock_resolve):
            response = client.get("/api/v1/live/strategy-signals/AAPL?timeframe=4h")

        assert response.status_code == 200
        assert response.json()["timeframe"] == "4h"
        assert mock_resolve.await_args.args[2] == "4h"


class TestStrategySignalsDbFallback:
    """Tests for merged bar resolution via resolve_bars."""

    def test_merged_bars_produce_strategies(self):
        bars = _make_bars(60)
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
            response = client.get("/api/v1/live/strategy-signals/BARC.L?timeframe=1w")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BARC.L"
        assert data["timeframe"] == "1w"
        assert data["bar_count"] == 60
        assert len(data["strategies"]) > 0

    def test_returns_empty_when_merged_bars_insufficient(self):
        bars = _make_bars(10)
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
            response = client.get("/api/v1/live/strategy-signals/AAPL?timeframe=1w")

        assert response.status_code == 200
        assert response.json()["strategies"] == []

    def test_merged_strategies_have_valid_signals(self):
        bars = _make_bars(60)
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
            response = client.get("/api/v1/live/strategy-signals/AAPL?timeframe=1w")

        assert response.status_code == 200
        for s in response.json()["strategies"]:
            assert s["signal"] in ("BUY", "SELL", "NEUTRAL")
            assert "params" in s

    def test_include_timeline_query_param(self):
        bars = _make_bars(60)
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
            response = client.get(
                "/api/v1/live/strategy-signals/AAPL?include_timeline=true&timeline_bars=40",
            )

        assert response.status_code == 200
        strategies = response.json()["strategies"]
        rsi = next(s for s in strategies if s["strategy"] == "rsi")
        assert len(rsi["signal_timeline"]) == 40
        assert rsi["signal_timeline"][-1]["signal"] in ("Buy", "Sell", "Neutral")

    def test_strategies_query_filters_evaluated_names(self):
        bars = _make_bars(60)
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
            response = client.get(
                "/api/v1/live/strategy-signals/AAPL?strategies=rsi,macd",
            )

        assert response.status_code == 200
        names = {s["strategy"] for s in response.json()["strategies"]}
        assert names == {"rsi", "macd"}

    def test_default_response_has_empty_timeline(self):
        bars = _make_bars(60)
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
            response = client.get("/api/v1/live/strategy-signals/AAPL")

        assert response.status_code == 200
        for s in response.json()["strategies"]:
            assert s.get("signal_timeline", []) == []

    def test_sma_cross_timeline_uses_stance_not_only_cross_events(self):
        bars = _make_bars(250)
        with patch("routes.live_trading.resolve_bars", new=AsyncMock(return_value=bars)):
            response = client.get(
                "/api/v1/live/strategy-signals/AAPL?timeframe=5m&include_timeline=true&timeline_bars=60",
            )

        assert response.status_code == 200
        sma = next(s for s in response.json()["strategies"] if s["strategy"] == "sma_cross")
        signals = {p["signal"] for p in sma["signal_timeline"]}
        assert len(sma["signal_timeline"]) == 60
        assert signals.issubset({"Buy", "Sell", "Neutral"})
        assert len(signals) >= 2
