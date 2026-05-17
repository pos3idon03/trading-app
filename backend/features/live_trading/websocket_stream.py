"""Alpaca WebSocket stream client for live stock and crypto market data."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from config import get_settings
from features.live_trading.stream_symbols import StreamPlan
from utils.logging import get_logger

logger = get_logger(__name__)


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


class AlpacaWebSocketStream:
    """Manages Alpaca StockDataStream and CryptoDataStream connections."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._queue: asyncio.Queue[TickData] = asyncio.Queue(maxsize=10_000)
        self._status = StreamStatus()
        self._alpaca_to_app: dict[str, str] = {}
        self._active_plan: StreamPlan | None = None
        self._stock_stream: Any = None
        self._crypto_stream: Any = None
        self._stock_task: asyncio.Task | None = None
        self._crypto_task: asyncio.Task | None = None
        self._stock_connected = False
        self._crypto_connected = False
        self._callbacks: list[Callable[[TickData], Awaitable[None]]] = []

    @property
    def queue(self) -> asyncio.Queue[TickData]:
        return self._queue

    @property
    def status(self) -> StreamStatus:
        return self._status

    def on_tick(self, callback: Callable[[TickData], Awaitable[None]]) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def set_tick_handler(self, callback: Callable[[TickData], Awaitable[None]]) -> None:
        """Replace tick handlers (avoids duplicate callbacks on stream restart)."""
        self._callbacks = [callback]

    async def start(self, plan: StreamPlan) -> None:
        if not plan.entries:
            logger.warning("stream_start_empty_plan")
            return

        if (
            self._status.connected
            and self._active_plan is not None
            and self._active_plan.app_symbol_set() == plan.app_symbol_set()
        ):
            return

        await self.stop(preserve_callbacks=True)

        self._active_plan = plan
        self._alpaca_to_app = {
            e.alpaca_symbol.upper(): e.app_symbol for e in plan.entries
        }
        self._status.subscribed_symbols = plan.app_symbols
        self._status.error = None

        stock_syms = plan.stock_alpaca_symbols()
        crypto_syms = plan.crypto_alpaca_symbols()

        if stock_syms:
            self._stock_task = asyncio.create_task(
                self._run_channel("stock", stock_syms),
            )
        if crypto_syms:
            self._crypto_task = asyncio.create_task(
                self._run_channel("crypto", crypto_syms),
            )

        self._sync_connected_flag()
        logger.info(
            "stream_starting",
            app_symbols=plan.app_symbols,
            stock=stock_syms,
            crypto=crypto_syms,
            skipped=plan.skipped,
        )

    async def stop(self, preserve_callbacks: bool = False) -> None:
        await self._stop_stream_instance(self._stock_stream)
        await self._stop_stream_instance(self._crypto_stream)
        self._stock_stream = None
        self._crypto_stream = None

        await self._cancel_task(self._stock_task)
        await self._cancel_task(self._crypto_task)
        self._stock_task = None
        self._crypto_task = None

        self._stock_connected = False
        self._crypto_connected = False
        self._status.connected = False
        self._status.stock_connected = False
        self._status.crypto_connected = False
        self._status.subscribed_symbols = []
        self._alpaca_to_app = {}
        self._active_plan = None

        if not preserve_callbacks:
            self._callbacks.clear()
        logger.info("stream_stopped")

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

    def _sync_connected_flag(self) -> None:
        self._status.connected = self._stock_connected or self._crypto_connected

    def _set_channel_connected(self, channel: str, connected: bool) -> None:
        if channel == "stock":
            self._stock_connected = connected
            self._status.stock_connected = connected
        else:
            self._crypto_connected = connected
            self._status.crypto_connected = connected
        self._sync_connected_flag()

    async def _run_channel(self, channel: str, alpaca_symbols: list[str]) -> None:
        max_retries = 5
        retry_delay = 2.0

        for attempt in range(max_retries):
            try:
                if channel == "stock":
                    await self._run_stock_once(alpaca_symbols)
                else:
                    await self._run_crypto_once(alpaca_symbols)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._set_channel_connected(channel, False)
                self._status.error = str(exc)
                self._status.reconnect_count += 1
                logger.error(
                    "stream_error",
                    channel=channel,
                    error=str(exc),
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    logger.error("stream_max_retries_exceeded", channel=channel)

    async def _run_stock_once(self, symbols: list[str]) -> None:
        from alpaca.data.live import StockDataStream

        stream = StockDataStream(
            api_key=self._settings.alpaca_api_key,
            secret_key=self._settings.alpaca_secret_key,
            url_override=self._settings.alpaca_data_ws_url,
        )
        self._stock_stream = stream
        stream.subscribe_bars(self._handle_bar, *symbols)
        self._set_channel_connected("stock", True)
        logger.info("stream_connected", channel="stock", symbols=symbols)
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
        self._set_channel_connected("crypto", True)
        logger.info("stream_connected", channel="crypto", symbols=symbols)
        await asyncio.to_thread(stream.run)

    async def _handle_bar(self, bar) -> None:
        raw = bar.symbol.upper() if bar.symbol else ""
        app_symbol = self._alpaca_to_app.get(raw, raw)

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
