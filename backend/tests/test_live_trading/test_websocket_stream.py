"""Unit tests for AlpacaWebSocketStream."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.live_trading.stream_symbols import StreamPlan, StreamSymbolEntry
from features.live_trading.websocket_stream import AlpacaWebSocketStream, TickData


def _plan(*entries: tuple[str, str, str]) -> StreamPlan:
    """(app_symbol, alpaca_symbol, channel) tuples."""
    plan = StreamPlan()
    plan.entries = [
        StreamSymbolEntry(app_symbol=a, alpaca_symbol=b, channel=c)
        for a, b, c in entries
    ]
    return plan


@pytest.fixture()
def stream() -> AlpacaWebSocketStream:
    with patch("features.live_trading.websocket_stream.get_settings") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            alpaca_api_key="test_key",
            alpaca_secret_key="test_secret",
            alpaca_data_ws_url="wss://test-stock",
            alpaca_crypto_data_ws_url="wss://test-crypto",
        )
        return AlpacaWebSocketStream()


class TestStreamStart:
    @pytest.mark.asyncio
    async def test_start_creates_stock_task(self, stream: AlpacaWebSocketStream):
        with patch.object(stream, "_run_channel", new=AsyncMock()):
            await stream.start(_plan(("AAPL", "AAPL", "stock")))
            assert stream._stock_task is not None
            assert stream.status.subscribed_symbols == ["AAPL"]

    @pytest.mark.asyncio
    async def test_start_creates_both_channel_tasks(self, stream: AlpacaWebSocketStream):
        with patch.object(stream, "_run_channel", new=AsyncMock()):
            plan = _plan(
                ("AAPL", "AAPL", "stock"),
                ("BTC-USD", "BTC/USD", "crypto"),
            )
            await stream.start(plan)
            assert stream._stock_task is not None
            assert stream._crypto_task is not None
            assert set(stream.status.subscribed_symbols) == {"AAPL", "BTC-USD"}

    @pytest.mark.asyncio
    async def test_start_noop_when_same_plan_connected(self, stream: AlpacaWebSocketStream):
        plan = _plan(("AAPL", "AAPL", "stock"))
        stream._status.connected = True
        stream._active_plan = plan
        stream._status.subscribed_symbols = ["AAPL"]

        with patch.object(stream, "_run_channel", new=AsyncMock()) as mock_run:
            await stream.start(plan)
            mock_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_restarts_when_symbol_set_grows(self, stream: AlpacaWebSocketStream):
        stream._status.connected = True
        stream._active_plan = _plan(("AAPL", "AAPL", "stock"))
        stream._status.subscribed_symbols = ["AAPL"]

        with patch.object(stream, "stop", new=AsyncMock()) as mock_stop:
            with patch.object(stream, "_run_channel", new=AsyncMock()):
                await stream.start(_plan(("AAPL", "AAPL", "stock"), ("MSFT", "MSFT", "stock")))
                mock_stop.assert_awaited_once()


class TestStreamStop:
    @pytest.mark.asyncio
    async def test_stop_resets_status(self, stream: AlpacaWebSocketStream):
        stream._status.connected = True
        stream._status.subscribed_symbols = ["AAPL"]
        await stream.stop()
        assert stream.status.connected is False
        assert stream.status.subscribed_symbols == []

    @pytest.mark.asyncio
    async def test_stop_preserves_callbacks_when_requested(self, stream: AlpacaWebSocketStream):
        cb = AsyncMock()
        stream._callbacks.append(cb)
        await stream.stop(preserve_callbacks=True)
        assert stream._callbacks == [cb]

    @pytest.mark.asyncio
    async def test_stop_clears_callbacks_by_default(self, stream: AlpacaWebSocketStream):
        stream._callbacks.append(AsyncMock())
        await stream.stop()
        assert stream._callbacks == []


class TestHandleBar:
    @pytest.mark.asyncio
    async def test_handle_bar_maps_alpaca_to_app_symbol(self, stream: AlpacaWebSocketStream):
        stream._alpaca_to_app = {"BTC/USD": "BTC-USD"}
        bar = MagicMock(
            symbol="BTC/USD",
            close=70000.0,
            volume=1,
            timestamp=datetime(2026, 5, 10, 14, 0, tzinfo=timezone.utc),
            vwap=None,
            open=69900.0,
            high=70100.0,
            low=69800.0,
        )
        await stream._handle_bar(bar)
        tick: TickData = stream.queue.get_nowait()
        assert tick.symbol == "BTC-USD"

    @pytest.mark.asyncio
    async def test_handle_bar_enqueues_tick(self, stream: AlpacaWebSocketStream):
        bar = MagicMock(
            symbol="AAPL",
            close=150.0,
            volume=1000,
            timestamp=datetime(2026, 5, 10, 14, 0, tzinfo=timezone.utc),
            vwap=149.5,
            open=148.0,
            high=151.0,
            low=147.0,
        )
        await stream._handle_bar(bar)
        tick: TickData = stream.queue.get_nowait()
        assert tick.symbol == "AAPL"
        assert tick.price == 150.0

    @pytest.mark.asyncio
    async def test_handle_bar_fires_callbacks(self, stream: AlpacaWebSocketStream):
        callback = AsyncMock()
        stream.on_tick(callback)
        bar = MagicMock(
            symbol="AAPL",
            close=150.0,
            volume=1000,
            timestamp=datetime(2026, 5, 10, 14, 0, tzinfo=timezone.utc),
            vwap=149.5,
            open=148.0,
            high=151.0,
            low=147.0,
        )
        await stream._handle_bar(bar)
        callback.assert_awaited_once()


class TestRunChannel:
    @pytest.mark.asyncio
    async def test_run_stock_uses_thread(self, stream: AlpacaWebSocketStream):
        mock_stream = MagicMock()
        mock_stream.run = MagicMock()

        with patch(
            "alpaca.data.live.StockDataStream",
            return_value=mock_stream,
        ):
            with patch("asyncio.to_thread", new=AsyncMock()) as mock_thread:
                mock_thread.return_value = None
                await stream._run_stock_once(["AAPL"])
                mock_thread.assert_awaited_once_with(mock_stream.run)
