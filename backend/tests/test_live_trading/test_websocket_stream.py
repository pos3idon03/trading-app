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
            stream_reconnect_base_delay_sec=0.01,
            stream_reconnect_max_delay_sec=0.05,
            stream_connection_limit_cooldown_sec=1.0,
            stream_stop_drain_sec=0.01,
        )
        return AlpacaWebSocketStream()


@pytest.fixture()
def rth_open():
    with patch(
        "features.live_trading.websocket_stream.should_run_stock_stream",
        return_value=True,
    ):
        yield


@pytest.fixture()
def rth_closed():
    with patch(
        "features.live_trading.websocket_stream.should_run_stock_stream",
        return_value=False,
    ):
        yield


class TestStreamReconcile:
    @pytest.mark.asyncio
    async def test_reconcile_creates_stock_task(
        self, stream: AlpacaWebSocketStream, rth_open,
    ):
        with patch.object(stream, "_run_channel", new=AsyncMock()):
            action = await stream.reconcile(_plan(("AAPL", "AAPL", "stock")))
            assert action == "restarted"
            assert stream._stock_task is not None
            assert stream.status.subscribed_symbols == ["AAPL"]
            if stream._stock_task and not stream._stock_task.done():
                stream._stock_task.cancel()
                try:
                    await stream._stock_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_reconcile_creates_both_channel_tasks(
        self, stream: AlpacaWebSocketStream, rth_open,
    ):
        with patch.object(stream, "_run_channel", new=AsyncMock()):
            plan = _plan(
                ("AAPL", "AAPL", "stock"),
                ("BTC-USD", "BTC/USD", "crypto"),
            )
            action = await stream.reconcile(plan)
            assert action == "restarted"
            assert stream._stock_task is not None
            assert stream._crypto_task is not None
            assert set(stream.status.subscribed_symbols) == {"AAPL", "BTC-USD"}
            for task in (stream._stock_task, stream._crypto_task):
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

    @pytest.mark.asyncio
    async def test_reconcile_noop_when_same_plan_healthy(
        self, stream: AlpacaWebSocketStream, rth_open,
    ):
        plan = _plan(("AAPL", "AAPL", "stock"))
        stream._desired_plan = plan
        stream._active_plan = plan
        stream._stock_connected = True
        stream._stock_task = asyncio.create_task(asyncio.sleep(3600))

        with patch.object(stream, "_start_channels", new=AsyncMock()) as mock_start:
            action = await stream.reconcile(plan)
            assert action == "noop"
            mock_start.assert_not_called()

        stream._stock_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await stream._stock_task

    @pytest.mark.asyncio
    async def test_reconcile_restarts_when_symbol_set_grows(self, stream: AlpacaWebSocketStream):
        plan = _plan(("AAPL", "AAPL", "stock"))
        stream._desired_plan = plan
        stream._stock_connected = True
        stream._stock_task = asyncio.create_task(asyncio.sleep(3600))

        with patch.object(stream, "_stop_channels", new=AsyncMock()) as mock_stop:
            with patch.object(stream, "_start_channels", new=AsyncMock()) as mock_start:
                action = await stream.reconcile(
                    _plan(("AAPL", "AAPL", "stock"), ("MSFT", "MSFT", "stock")),
                )
                assert action == "restarted"
                mock_stop.assert_awaited_once()
                mock_start.assert_awaited_once()

        stream._stock_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await stream._stock_task

    @pytest.mark.asyncio
    async def test_reconcile_schedules_reconnect_when_unhealthy(
        self, stream: AlpacaWebSocketStream, rth_open,
    ):
        plan = _plan(("AAPL", "AAPL", "stock"))
        stream._desired_plan = plan
        stream._active_plan = plan

        with patch.object(stream, "_ensure_reconnect_task") as mock_reconnect:
            action = await stream.reconcile(plan)
            assert action == "reconnect_scheduled"
            mock_reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconcile_returns_reconnect_in_progress(
        self, stream: AlpacaWebSocketStream, rth_open,
    ):
        plan = _plan(("AAPL", "AAPL", "stock"))
        stream._desired_plan = plan
        stream._reconnect_task = asyncio.create_task(asyncio.sleep(3600))

        with patch.object(stream, "_ensure_reconnect_task") as mock_ensure:
            action = await stream.reconcile(plan)
            assert action == "reconnect_in_progress"
            mock_ensure.assert_not_called()

        stream._reconnect_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await stream._reconnect_task

    @pytest.mark.asyncio
    async def test_reconcile_returns_cooldown_when_in_cooldown(
        self, stream: AlpacaWebSocketStream, rth_open,
    ):
        plan = _plan(("AAPL", "AAPL", "stock"))
        stream._desired_plan = plan
        stream._cooldown_until = datetime.now(timezone.utc).replace(year=2099)

        action = await stream.reconcile(plan)
        assert action == "cooldown"

    @pytest.mark.asyncio
    async def test_start_alias_delegates_to_reconcile(self, stream: AlpacaWebSocketStream):
        with patch.object(stream, "reconcile", new=AsyncMock(return_value="noop")) as mock_reconcile:
            await stream.start(_plan(("AAPL", "AAPL", "stock")))
            mock_reconcile.assert_awaited_once()


class TestStreamStop:
    @pytest.mark.asyncio
    async def test_stop_resets_status(self, stream: AlpacaWebSocketStream):
        stream._status.connected = True
        stream._status.subscribed_symbols = ["AAPL"]
        with patch.object(stream, "_stop_channels", new=AsyncMock()) as mock_stop:
            with patch("asyncio.sleep", new=AsyncMock()):
                await stream.stop()
            mock_stop.assert_awaited_once()
        assert stream._desired_plan is None

    @pytest.mark.asyncio
    async def test_stop_preserves_callbacks_when_requested(self, stream: AlpacaWebSocketStream):
        cb = AsyncMock()
        stream._callbacks.append(cb)
        with patch.object(stream, "_stop_channels", new=AsyncMock()):
            await stream.stop(preserve_callbacks=True)
        assert stream._callbacks == [cb]

    @pytest.mark.asyncio
    async def test_stop_clears_callbacks_by_default(self, stream: AlpacaWebSocketStream):
        stream._callbacks.append(AsyncMock())
        with patch.object(stream, "_stop_channels", new=AsyncMock()):
            await stream.stop()
        assert stream._callbacks == []

    @pytest.mark.asyncio
    async def test_stop_cancels_reconnect_task(self, stream: AlpacaWebSocketStream):
        stream._reconnect_task = asyncio.create_task(asyncio.sleep(3600))
        with patch.object(stream, "_stop_channels", new=AsyncMock()):
            await stream.stop()
        assert stream._reconnect_task is None
        assert stream.status.reconnecting is False


class TestHandleBar:
    @pytest.mark.asyncio
    async def test_connected_false_until_first_bar(self, stream: AlpacaWebSocketStream):
        assert stream.status.connected is False
        assert stream.status.stock_connected is False

    @pytest.mark.asyncio
    async def test_handle_bar_sets_connected_on_first_bar(self, stream: AlpacaWebSocketStream):
        stream._symbol_to_channel = {"AAPL": "stock"}
        stream._alpaca_to_app = {"AAPL": "AAPL"}
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
        assert stream.status.stock_connected is True
        assert stream.status.connected is True

    @pytest.mark.asyncio
    async def test_handle_bar_maps_alpaca_to_app_symbol(self, stream: AlpacaWebSocketStream):
        stream._alpaca_to_app = {"BTC/USD": "BTC-USD"}
        stream._symbol_to_channel = {"BTC-USD": "crypto"}
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
    async def test_handle_bar_fires_callbacks(self, stream: AlpacaWebSocketStream):
        callback = AsyncMock()
        stream.on_tick(callback)
        stream._symbol_to_channel = {"AAPL": "stock"}
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
    async def test_run_channel_single_attempt_on_failure(self, stream: AlpacaWebSocketStream):
        stream._desired_plan = _plan(("AAPL", "AAPL", "stock"))
        with patch.object(
            stream,
            "_run_stock_once",
            new=AsyncMock(side_effect=ValueError("socket closed")),
        ) as mock_run:
            with patch.object(stream, "_ensure_reconnect_task") as mock_reconnect:
                await stream._run_channel("stock", ["AAPL"])
                mock_run.assert_awaited_once()
                mock_reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_limit_sets_cooldown(self, stream: AlpacaWebSocketStream):
        stream._mark_channel_down("stock", ValueError("connection limit exceeded"))
        assert stream._cooldown_until is not None
        assert stream.status.cooldown_until is not None

    @pytest.mark.asyncio
    async def test_run_stock_uses_thread(self, stream: AlpacaWebSocketStream):
        mock_alpaca = MagicMock()
        mock_alpaca.run = MagicMock()

        with patch(
            "alpaca.data.live.StockDataStream",
            return_value=mock_alpaca,
        ):
            with patch("asyncio.to_thread", new=AsyncMock()) as mock_thread:
                mock_thread.return_value = None
                await stream._run_stock_once(["AAPL"])
                mock_thread.assert_awaited_once_with(mock_alpaca.run)
        assert stream.status.stock_connected is False


class TestOffHoursStockStream:
    @pytest.mark.asyncio
    async def test_off_hours_skips_stock_task(
        self, stream: AlpacaWebSocketStream, rth_closed,
    ):
        plan = _plan(
            ("AAPL", "AAPL", "stock"),
            ("BTC-USD", "BTC/USD", "crypto"),
        )
        with patch.object(stream, "_run_channel", new=AsyncMock()):
            await stream.reconcile(plan)
            assert stream._stock_task is None
            assert stream._crypto_task is not None
            if stream._crypto_task and not stream._crypto_task.done():
                stream._crypto_task.cancel()
                try:
                    await stream._crypto_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_off_hours_healthy_with_crypto_connected(
        self, stream: AlpacaWebSocketStream, rth_closed,
    ):
        plan = _plan(
            ("AAPL", "AAPL", "stock"),
            ("BTC-USD", "BTC/USD", "crypto"),
        )
        stream._desired_plan = plan
        stream._crypto_connected = True
        stream._crypto_task = asyncio.create_task(asyncio.sleep(3600))
        assert stream._is_healthy() is True
        stream._crypto_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await stream._crypto_task

    @pytest.mark.asyncio
    async def test_rth_open_requires_stock_channel(
        self, stream: AlpacaWebSocketStream, rth_open,
    ):
        plan = _plan(("AAPL", "AAPL", "stock"))
        stream._desired_plan = plan
        assert stream._is_healthy() is False


class TestPartialReconnect:
    @pytest.mark.asyncio
    async def test_unhealthy_channels_excludes_healthy_crypto(
        self, stream: AlpacaWebSocketStream, rth_open,
    ):
        plan = _plan(
            ("AAPL", "AAPL", "stock"),
            ("BTC-USD", "BTC/USD", "crypto"),
        )
        stream._crypto_connected = True
        stream._crypto_task = asyncio.create_task(asyncio.sleep(3600))
        assert stream._unhealthy_channels(plan) == ["stock"]
        stream._crypto_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await stream._crypto_task

    @pytest.mark.asyncio
    async def test_partial_stop_preserves_last_tick_at(self, stream: AlpacaWebSocketStream):
        stream._status.last_tick_at = datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc)
        with patch("asyncio.sleep", new=AsyncMock()):
            await stream._stop_channel("stock")
        assert stream._status.last_tick_at is not None

    @pytest.mark.asyncio
    async def test_full_stop_clears_last_tick_at(self, stream: AlpacaWebSocketStream):
        stream._status.last_tick_at = datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc)
        with patch.object(stream, "_stop_channel", new=AsyncMock()):
            await stream._stop_channels(clear_desired=False)
        assert stream._status.last_tick_at is None

    @pytest.mark.asyncio
    async def test_run_channel_skips_reconnect_during_cooldown(
        self, stream: AlpacaWebSocketStream,
    ):
        stream._desired_plan = _plan(("AAPL", "AAPL", "stock"))
        stream._cooldown_until = datetime.now(timezone.utc).replace(year=2099)
        with patch.object(
            stream,
            "_run_stock_once",
            new=AsyncMock(side_effect=ValueError("connection limit exceeded")),
        ):
            with patch.object(stream, "_ensure_reconnect_task") as mock_reconnect:
                await stream._run_channel("stock", ["AAPL"])
                mock_reconnect.assert_not_called()
