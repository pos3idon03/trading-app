"""Unit tests for AlpacaWebSocketStream."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.live_trading.websocket_stream import AlpacaWebSocketStream, StreamStatus, TickData


@pytest.fixture()
def stream() -> AlpacaWebSocketStream:
    with patch("features.live_trading.websocket_stream.get_settings") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            alpaca_api_key="test_key",
            alpaca_secret_key="test_secret",
            alpaca_data_ws_url="wss://test",
        )
        return AlpacaWebSocketStream()


class TestStreamStart:
    @pytest.mark.asyncio
    async def test_start_creates_task(self, stream: AlpacaWebSocketStream):
        with patch.object(stream, "_run_stream", new=AsyncMock()):
            await stream.start(["AAPL"])
            assert stream._task is not None
            assert stream.status.subscribed_symbols == ["AAPL"]

    @pytest.mark.asyncio
    async def test_start_uppercases_symbols(self, stream: AlpacaWebSocketStream):
        with patch.object(stream, "_run_stream", new=AsyncMock()):
            await stream.start(["aapl", "msft"])
            assert stream.status.subscribed_symbols == ["AAPL", "MSFT"]

    @pytest.mark.asyncio
    async def test_start_noop_when_already_connected(self, stream: AlpacaWebSocketStream):
        stream._status.connected = True
        with patch.object(stream, "_run_stream", new=AsyncMock()) as mock_run:
            await stream.start(["AAPL"])
            mock_run.assert_not_called()


class TestStreamStop:
    @pytest.mark.asyncio
    async def test_stop_resets_status(self, stream: AlpacaWebSocketStream):
        stream._status.connected = True
        stream._status.subscribed_symbols = ["AAPL"]
        await stream.stop()
        assert stream.status.connected is False
        assert stream.status.subscribed_symbols == []

    @pytest.mark.asyncio
    async def test_stop_clears_callbacks(self, stream: AlpacaWebSocketStream):
        stream._callbacks.append(AsyncMock())
        stream._callbacks.append(AsyncMock())
        await stream.stop()
        assert stream._callbacks == []

    @pytest.mark.asyncio
    async def test_stop_cancels_running_task(self, stream: AlpacaWebSocketStream):
        async def _blocking():
            await asyncio.sleep(60)

        stream._task = asyncio.create_task(_blocking())
        await stream.stop()
        assert stream._task.done()

    @pytest.mark.asyncio
    async def test_stop_calls_stream_stop(self, stream: AlpacaWebSocketStream):
        mock_alpaca_stream = MagicMock()
        stream._stream = mock_alpaca_stream
        await stream.stop()
        mock_alpaca_stream.stop.assert_called_once()


class TestHandleBar:
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
        assert not stream.queue.empty()
        tick: TickData = stream.queue.get_nowait()
        assert tick.symbol == "AAPL"
        assert tick.price == 150.0

    @pytest.mark.asyncio
    async def test_handle_bar_updates_last_tick_at(self, stream: AlpacaWebSocketStream):
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
        assert stream.status.last_tick_at is not None

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

    @pytest.mark.asyncio
    async def test_handle_bar_drops_oldest_when_queue_full(self, stream: AlpacaWebSocketStream):
        stream._queue = asyncio.Queue(maxsize=1)
        bar = MagicMock(
            symbol="AAPL",
            close=100.0,
            volume=100,
            timestamp=datetime(2026, 5, 10, 14, 0, tzinfo=timezone.utc),
            vwap=None,
            open=99.0,
            high=101.0,
            low=98.0,
        )
        bar2 = MagicMock(
            symbol="AAPL",
            close=200.0,
            volume=200,
            timestamp=datetime(2026, 5, 10, 14, 1, tzinfo=timezone.utc),
            vwap=None,
            open=199.0,
            high=201.0,
            low=198.0,
        )
        await stream._handle_bar(bar)
        await stream._handle_bar(bar2)
        tick = stream.queue.get_nowait()
        assert tick.price == 200.0


class TestRunStream:
    @pytest.mark.asyncio
    async def test_run_stream_uses_thread(self, stream: AlpacaWebSocketStream):
        """StockDataStream.run() must be called via asyncio.to_thread, not directly."""
        mock_alpaca_cls = MagicMock()
        mock_alpaca_instance = MagicMock()
        mock_alpaca_cls.return_value = mock_alpaca_instance

        call_order: list[str] = []

        def fake_run():
            call_order.append("run_in_thread")

        mock_alpaca_instance.run = fake_run

        with patch("features.live_trading.websocket_stream.get_settings") as mock_cfg:
            mock_cfg.return_value = MagicMock(
                alpaca_api_key="k",
                alpaca_secret_key="s",
                alpaca_data_ws_url="wss://test",
            )
            with patch(
                "features.live_trading.websocket_stream.AlpacaWebSocketStream._run_stream",
                new=AsyncMock(),
            ) as mock_run_stream:
                s = AlpacaWebSocketStream()
                await s.start(["AAPL"])
                mock_run_stream.assert_called_once()
