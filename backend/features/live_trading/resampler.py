"""Resampling engine: groups live tick data into OHLCV bars at multiple timeframes."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Awaitable

from utils.logging import get_logger

logger = get_logger(__name__)

TIMEFRAME_DELTAS: dict[str, timedelta] = {
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
}


@dataclass
class OHLCVBar:
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float | None
    bar_start: datetime
    bar_end: datetime
    tick_count: int = 0


@dataclass
class _BarBuffer:
    open: float = 0.0
    high: float = float("-inf")
    low: float = float("inf")
    close: float = 0.0
    volume: int = 0
    vwap_numerator: float = 0.0
    tick_count: int = 0
    bar_start: datetime | None = None
    bar_end: datetime | None = None


def _align_bar_start(ts: datetime, delta: timedelta) -> datetime:
    """Align a timestamp to the beginning of its bar window."""
    epoch = datetime(2000, 1, 1, tzinfo=timezone.utc)
    elapsed = (ts - epoch).total_seconds()
    period = delta.total_seconds()
    aligned_secs = (elapsed // period) * period
    return epoch + timedelta(seconds=aligned_secs)


def _update_buffer(buf: _BarBuffer, price: float, volume: int, vwap: float | None) -> None:
    if buf.tick_count == 0:
        buf.open = price
        buf.high = price
        buf.low = price
    else:
        buf.high = max(buf.high, price)
        buf.low = min(buf.low, price)

    buf.close = price
    buf.volume += volume
    buf.tick_count += 1
    if vwap is not None:
        buf.vwap_numerator += vwap * volume


def _buffer_to_bar(
    symbol: str, timeframe: str, buf: _BarBuffer, bar_start: datetime, bar_end: datetime,
) -> OHLCVBar:
    vwap = (buf.vwap_numerator / buf.volume) if buf.volume > 0 else None
    return OHLCVBar(
        symbol=symbol,
        timeframe=timeframe,
        open=buf.open,
        high=buf.high,
        low=buf.low,
        close=buf.close,
        volume=buf.volume,
        vwap=vwap,
        bar_start=bar_start,
        bar_end=bar_end,
        tick_count=buf.tick_count,
    )


BarCallback = Callable[[OHLCVBar], Awaitable[None]]


class ResamplingEngine:
    """Accumulates ticks and emits OHLCV bars when a timeframe period closes."""

    def __init__(self, timeframes: list[str] | None = None) -> None:
        self._timeframes = timeframes or list(TIMEFRAME_DELTAS.keys())
        self._buffers: dict[str, dict[str, _BarBuffer]] = defaultdict(
            lambda: {tf: _BarBuffer() for tf in self._timeframes}
        )
        self._callbacks: list[BarCallback] = []
        self._bar_history: dict[str, dict[str, list[OHLCVBar]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._max_history = 250

    @property
    def bar_history(self) -> dict[str, dict[str, list[OHLCVBar]]]:
        return dict(self._bar_history)

    def on_bar(self, callback: BarCallback) -> None:
        self._callbacks.append(callback)

    def get_bars(self, symbol: str, timeframe: str, limit: int = 200) -> list[OHLCVBar]:
        bars = self._bar_history.get(symbol, {}).get(timeframe, [])
        return bars[-limit:]

    async def process_tick(
        self,
        symbol: str,
        price: float,
        volume: int,
        timestamp: datetime,
        vwap: float | None = None,
        high: float | None = None,
        low: float | None = None,
    ) -> list[OHLCVBar]:
        """Process a single tick; returns any completed bars."""
        completed: list[OHLCVBar] = []
        tick_high = high if high is not None else price
        tick_low = low if low is not None else price

        for tf in self._timeframes:
            delta = TIMEFRAME_DELTAS[tf]
            bar_start = _align_bar_start(timestamp, delta)
            bar_end = bar_start + delta
            buf = self._buffers[symbol][tf]

            if buf.bar_start is not None and bar_start != buf.bar_start:
                bar = _buffer_to_bar(symbol, tf, buf, buf.bar_start, buf.bar_start + delta)
                completed.append(bar)
                self._store_bar(bar)
                self._buffers[symbol][tf] = _BarBuffer()
                buf = self._buffers[symbol][tf]

            if buf.bar_start is None:
                buf.bar_start = bar_start
                buf.bar_end = bar_end

            _update_buffer(buf, price, volume, vwap)
            buf.high = max(buf.high, tick_high)
            buf.low = min(buf.low, tick_low)

        for bar in completed:
            for cb in self._callbacks:
                try:
                    await cb(bar)
                except Exception as exc:
                    logger.error("bar_callback_error", error=str(exc), bar=bar.symbol)

        return completed

    def _store_bar(self, bar: OHLCVBar) -> None:
        history = self._bar_history[bar.symbol][bar.timeframe]
        history.append(bar)
        if len(history) > self._max_history:
            self._bar_history[bar.symbol][bar.timeframe] = history[-self._max_history:]
