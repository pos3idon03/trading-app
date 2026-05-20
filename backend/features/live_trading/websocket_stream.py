"""Alpaca WebSocket stream client for live stock and crypto market data."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from config import get_settings
from features.execution.market_hours import should_run_stock_stream
from features.live_trading.stream_symbols import StreamPlan
from utils.logging import get_logger

logger = get_logger(__name__)

CONNECTION_LIMIT_MARKER = "connection limit exceeded"
CONNECT_TIMEOUT_SEC = 30.0


@dataclass
class TickData:
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    vwap: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None


@dataclass
class StreamStatus:
    connected: bool = False
    stock_connected: bool = False
    crypto_connected: bool = False
    subscribed_symbols: list[str] = field(default_factory=list)
    last_tick_at: datetime | None = None
    error: str | None = None
    reconnect_count: int = 0
    reconnecting: bool = False
    cooldown_until: datetime | None = None


class AlpacaWebSocketStream:
    """Manages Alpaca StockDataStream and CryptoDataStream connections."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._queue: asyncio.Queue[TickData] = asyncio.Queue(maxsize=10_000)
        self._status = StreamStatus()
        self._lock = asyncio.Lock()
        self._alpaca_to_app: dict[str, str] = {}
        self._symbol_to_channel: dict[str, str] = {}
        self._desired_plan: StreamPlan | None = None
        self._active_plan: StreamPlan | None = None
        self._stock_stream: Any = None
        self._crypto_stream: Any = None
        self._stock_task: asyncio.Task | None = None
        self._crypto_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._stock_connected = False
        self._crypto_connected = False
        self._channel_authenticated: dict[str, bool] = {"stock": False, "crypto": False}
        self._channel_started_at: dict[str, datetime | None] = {"stock": None, "crypto": None}
        self._cooldown_until: datetime | None = None
        self._backoff_sec = self._settings.stream_reconnect_base_delay_sec
        self._callbacks: list[Callable[[TickData], Awaitable[None]]] = []

    @property
    def queue(self) -> asyncio.Queue[TickData]:
        return self._queue

    @property
    def status(self) -> StreamStatus:
        self._sync_status_flags()
        return self._status

    def on_tick(self, callback: Callable[[TickData], Awaitable[None]]) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def set_tick_handler(self, callback: Callable[[TickData], Awaitable[None]]) -> None:
        """Replace tick handlers (avoids duplicate callbacks on stream restart)."""
        self._callbacks = [callback]

    async def reconcile(self, plan: StreamPlan) -> str:
        """Keep one long-lived connection; reconnect only when plan or health requires it."""
        async with self._lock:
            if not plan.entries:
                await self._stop_all()
                return "stopped"

            plan_changed = (
                self._desired_plan is None
                or self._desired_plan.app_symbol_set() != plan.app_symbol_set()
            )
            self._desired_plan = plan
            self._apply_plan_metadata(plan)

            if plan_changed:
                await self._cancel_reconnect_task()
                await self._stop_channels(clear_desired=False)
                await self._start_channels(plan)
                return "restarted"

            if self._is_healthy():
                return "noop"

            if self._is_reconnect_in_progress():
                return "reconnect_in_progress"

            if self._in_cooldown():
                return "cooldown"

            self._ensure_reconnect_task()
            return "reconnect_scheduled"

    async def start(self, plan: StreamPlan) -> None:
        """Backward-compatible alias for reconcile()."""
        await self.reconcile(plan)

    async def stop(self, preserve_callbacks: bool = False) -> None:
        async with self._lock:
            await self._stop_all(preserve_callbacks=preserve_callbacks)

    def _apply_plan_metadata(self, plan: StreamPlan) -> None:
        self._active_plan = plan
        self._alpaca_to_app = {
            e.alpaca_symbol.upper(): e.app_symbol for e in plan.entries
        }
        self._symbol_to_channel = {e.app_symbol: e.channel for e in plan.entries}
        self._status.subscribed_symbols = plan.app_symbols

    def _symbols_for_channel(self, plan: StreamPlan, channel: str) -> list[str]:
        if channel == "stock":
            return plan.stock_alpaca_symbols()
        return plan.crypto_alpaca_symbols()

    def _channels_requiring_health(self, plan: StreamPlan) -> list[str]:
        channels: list[str] = []
        if plan.crypto_alpaca_symbols():
            channels.append("crypto")
        if plan.stock_alpaca_symbols() and should_run_stock_stream():
            channels.append("stock")
        return channels

    def _unhealthy_channels(self, plan: StreamPlan) -> list[str]:
        return [
            ch for ch in self._channels_requiring_health(plan)
            if not self._channel_healthy(ch, self._symbols_for_channel(plan, ch))
        ]

    def _is_healthy(self) -> bool:
        plan = self._desired_plan
        if plan is None:
            return False
        return not self._unhealthy_channels(plan)

    def _channel_healthy(self, channel: str, symbols: list[str]) -> bool:
        if not symbols:
            return True
        if channel == "stock" and not should_run_stock_stream():
            return True
        task = self._stock_task if channel == "stock" else self._crypto_task
        if task is None or task.done():
            return False
        connected = self._stock_connected if channel == "stock" else self._crypto_connected
        if connected:
            return True
        return self._within_connect_timeout(channel)

    def _within_connect_timeout(self, channel: str) -> bool:
        started = self._channel_started_at.get(channel)
        if started is None:
            return True
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        return elapsed < CONNECT_TIMEOUT_SEC

    def _in_cooldown(self) -> bool:
        if self._cooldown_until is None:
            return False
        return datetime.now(timezone.utc) < self._cooldown_until

    def _is_reconnect_in_progress(self) -> bool:
        return self._reconnect_task is not None and not self._reconnect_task.done()

    def _sync_status_flags(self) -> None:
        self._status.cooldown_until = self._cooldown_until
        self._status.reconnecting = self._is_reconnect_in_progress()

    async def _stop_all(self, preserve_callbacks: bool = False) -> None:
        await self._cancel_reconnect_task()
        self._desired_plan = None
        await self._stop_channels(clear_desired=True)
        if not preserve_callbacks:
            self._callbacks.clear()
        logger.info("stream_stopped")

    async def _stop_channels(self, clear_desired: bool) -> None:
        await self._stop_channel("stock")
        await self._stop_channel("crypto")
        self._status.last_tick_at = None

        if clear_desired:
            self._active_plan = None
            self._alpaca_to_app = {}
            self._symbol_to_channel = {}
            self._status.subscribed_symbols = []

    async def _stop_channel(self, channel: str) -> None:
        task = self._stock_task if channel == "stock" else self._crypto_task
        stream = self._stock_stream if channel == "stock" else self._crypto_stream

        await self._cancel_task(task)
        if channel == "stock":
            self._stock_task = None
        else:
            self._crypto_task = None

        await self._stop_stream_instance(stream)
        if channel == "stock":
            self._stock_stream = None
        else:
            self._crypto_stream = None

        await asyncio.sleep(self._settings.stream_stop_drain_sec)
        self._reset_single_channel_state(channel)

    def _reset_single_channel_state(self, channel: str) -> None:
        if channel == "stock":
            self._stock_connected = False
            self._status.stock_connected = False
        else:
            self._crypto_connected = False
            self._status.crypto_connected = False
        self._channel_authenticated[channel] = False
        self._channel_started_at[channel] = None
        self._sync_connected_flag()

    def _sync_connected_flag(self) -> None:
        self._status.connected = self._stock_connected or self._crypto_connected

    async def _start_channels(self, plan: StreamPlan) -> None:
        self._status.error = None
        stock_syms = plan.stock_alpaca_symbols()
        crypto_syms = plan.crypto_alpaca_symbols()

        if stock_syms and should_run_stock_stream():
            await self._start_channel("stock", plan)
        if crypto_syms:
            await self._start_channel("crypto", plan)

        logger.info(
            "stream_starting",
            app_symbols=plan.app_symbols,
            stock=stock_syms if should_run_stock_stream() else [],
            crypto=crypto_syms,
            skipped=plan.skipped,
        )

    async def _start_channel(self, channel: str, plan: StreamPlan) -> None:
        symbols = self._symbols_for_channel(plan, channel)
        if not symbols:
            return
        self._channel_started_at[channel] = datetime.now(timezone.utc)
        task = asyncio.create_task(self._run_channel(channel, symbols))
        if channel == "stock":
            self._stock_task = task
        else:
            self._crypto_task = task

    def _ensure_reconnect_task(self) -> None:
        if self._is_reconnect_in_progress():
            return
        self._status.reconnecting = True
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _cancel_reconnect_task(self) -> None:
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        self._reconnect_task = None
        self._status.reconnecting = False

    async def _reconnect_loop(self) -> None:
        try:
            while self._desired_plan and not self._is_healthy():
                if self._in_cooldown():
                    wait_sec = (
                        self._cooldown_until - datetime.now(timezone.utc)
                    ).total_seconds()
                    await asyncio.sleep(max(wait_sec, 0.1))
                    continue

                await asyncio.sleep(self._backoff_sec)

                async with self._lock:
                    plan = self._desired_plan
                    if not plan or self._is_healthy() or self._in_cooldown():
                        continue
                    unhealthy = self._unhealthy_channels(plan)
                    if not unhealthy:
                        continue
                    for channel in unhealthy:
                        await self._stop_channel(channel)
                        await self._start_channel(channel, plan)

                await asyncio.sleep(2)

                if self._is_healthy():
                    self._backoff_sec = self._settings.stream_reconnect_base_delay_sec
                    break

                self._backoff_sec = min(
                    self._backoff_sec * 2,
                    self._settings.stream_reconnect_max_delay_sec,
                )
        except asyncio.CancelledError:
            raise
        finally:
            self._status.reconnecting = False

    async def _cancel_task(self, task: asyncio.Task | None) -> None:
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _stop_stream_instance(self, stream: Any) -> None:
        if stream is None:
            return
        try:
            stream.stop()
        except Exception as exc:
            logger.warning("stream_stop_error", error=str(exc))

    def _set_channel_connected(self, channel: str, connected: bool) -> None:
        if channel == "stock":
            self._stock_connected = connected
            self._status.stock_connected = connected
        else:
            self._crypto_connected = connected
            self._status.crypto_connected = connected
        self._sync_connected_flag()

    async def _run_channel(self, channel: str, alpaca_symbols: list[str]) -> None:
        cancelled = False
        try:
            if channel == "stock":
                await self._run_stock_once(alpaca_symbols)
            else:
                await self._run_crypto_once(alpaca_symbols)
        except asyncio.CancelledError:
            cancelled = True
            raise
        except Exception as exc:
            self._mark_channel_down(channel, exc)
        finally:
            if not cancelled and self._desired_plan is not None and not self._in_cooldown():
                self._ensure_reconnect_task()

    def _mark_channel_down(self, channel: str, exc: Exception) -> None:
        self._set_channel_connected(channel, False)
        self._channel_authenticated[channel] = False
        self._status.error = str(exc)
        self._status.reconnect_count += 1
        logger.error("stream_error", channel=channel, error=str(exc))

        if CONNECTION_LIMIT_MARKER in str(exc).lower():
            cooldown = self._settings.stream_connection_limit_cooldown_sec
            self._cooldown_until = datetime.now(timezone.utc) + timedelta(seconds=cooldown)
            self._status.cooldown_until = self._cooldown_until
            logger.warning("stream_connection_limit_cooldown", cooldown_sec=cooldown)

    async def _run_stock_once(self, symbols: list[str]) -> None:
        from alpaca.data.live import StockDataStream

        stream = StockDataStream(
            api_key=self._settings.alpaca_api_key,
            secret_key=self._settings.alpaca_secret_key,
            url_override=self._settings.alpaca_data_ws_url,
        )
        self._stock_stream = stream
        stream.subscribe_bars(self._handle_bar, *symbols)
        logger.info("stream_connecting", channel="stock", symbols=symbols)
        await asyncio.to_thread(stream.run)

    async def _run_crypto_once(self, symbols: list[str]) -> None:
        from alpaca.data.enums import CryptoFeed
        from alpaca.data.live import CryptoDataStream

        crypto_url = (self._settings.alpaca_crypto_data_ws_url or "").rstrip("/")
        if crypto_url.endswith("/us"):
            stream = CryptoDataStream(
                api_key=self._settings.alpaca_api_key,
                secret_key=self._settings.alpaca_secret_key,
                url_override=crypto_url,
            )
        else:
            stream = CryptoDataStream(
                api_key=self._settings.alpaca_api_key,
                secret_key=self._settings.alpaca_secret_key,
                feed=CryptoFeed.US,
            )
        self._crypto_stream = stream
        stream.subscribe_bars(self._handle_bar, *symbols)
        logger.info("stream_connecting", channel="crypto", symbols=symbols)
        await asyncio.to_thread(stream.run)

    async def _handle_bar(self, bar) -> None:
        raw = bar.symbol.upper() if bar.symbol else ""
        app_symbol = self._alpaca_to_app.get(raw, raw)
        channel = self._symbol_to_channel.get(app_symbol)

        if channel and not self._channel_authenticated.get(channel):
            self._channel_authenticated[channel] = True
            self._set_channel_connected(channel, True)
            logger.info("stream_authenticated", channel=channel)

        tick = TickData(
            symbol=app_symbol,
            price=float(bar.close),
            volume=int(bar.volume),
            timestamp=bar.timestamp.replace(tzinfo=timezone.utc)
            if bar.timestamp.tzinfo is None
            else bar.timestamp,
            vwap=float(bar.vwap) if hasattr(bar, "vwap") and bar.vwap else None,
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
        )

        try:
            self._queue.put_nowait(tick)
        except asyncio.QueueFull:
            self._queue.get_nowait()
            self._queue.put_nowait(tick)

        self._status.last_tick_at = tick.timestamp

        for cb in self._callbacks:
            try:
                await cb(tick)
            except Exception as exc:
                logger.error("tick_callback_error", error=str(exc))


_instance: AlpacaWebSocketStream | None = None


def get_stream() -> AlpacaWebSocketStream:
    global _instance
    if _instance is None:
        _instance = AlpacaWebSocketStream()
    return _instance
