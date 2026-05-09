"""Alpaca WebSocket stream client for live market data."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Awaitable

from config import get_settings
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
    subscribed_symbols: list[str] = field(default_factory=list)
    last_tick_at: datetime | None = None
    error: str | None = None
    reconnect_count: int = 0


class AlpacaWebSocketStream:
    """Manages an Alpaca StockDataStream connection and publishes ticks."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._queue: asyncio.Queue[TickData] = asyncio.Queue(maxsize=10_000)
        self._status = StreamStatus()
        self._stream = None
        self._task: asyncio.Task | None = None
        self._callbacks: list[Callable[[TickData], Awaitable[None]]] = []

    @property
    def queue(self) -> asyncio.Queue[TickData]:
        return self._queue

    @property
    def status(self) -> StreamStatus:
        return self._status

    def on_tick(self, callback: Callable[[TickData], Awaitable[None]]) -> None:
        self._callbacks.append(callback)

    async def start(self, symbols: list[str]) -> None:
        if self._status.connected:
            logger.warning("stream_already_connected")
            return

        self._status.subscribed_symbols = [s.upper() for s in symbols]
        self._task = asyncio.create_task(self._run_stream())
        logger.info("stream_starting", symbols=self._status.subscribed_symbols)

    async def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
            except Exception as exc:
                logger.warning("stream_stop_error", error=str(exc))

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._status.connected = False
        self._status.subscribed_symbols = []
        self._callbacks.clear()
        logger.info("stream_stopped")

    async def _run_stream(self) -> None:
        from alpaca.data.live import StockDataStream

        max_retries = 5
        retry_delay = 2.0

        for attempt in range(max_retries):
            try:
                self._stream = StockDataStream(
                    api_key=self._settings.alpaca_api_key,
                    secret_key=self._settings.alpaca_secret_key,
                    url_override=self._settings.alpaca_data_ws_url,
                )
                self._stream.subscribe_bars(
                    self._handle_bar,
                    *self._status.subscribed_symbols,
                )
                self._status.connected = True
                self._status.error = None
                logger.info("stream_connected", attempt=attempt + 1)

                await asyncio.to_thread(self._stream.run)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._status.connected = False
                self._status.error = str(exc)
                self._status.reconnect_count += 1
                logger.error(
                    "stream_error",
                    error=str(exc),
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    logger.error("stream_max_retries_exceeded")

    async def _handle_bar(self, bar) -> None:
        tick = TickData(
            symbol=bar.symbol,
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
