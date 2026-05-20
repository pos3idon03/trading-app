"""Persist completed live resampler bars to the OHLCV hypertable."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from dal.market_data_dal import bulk_insert_ohlcv, get_asset_id_by_symbol
from db import AsyncSessionLocal
from dtos.market_data_dto import OHLCVRecord
from features.live_trading.resampler import OHLCVBar, ResamplingEngine
from utils.logging import get_logger

logger = get_logger(__name__)

_PERSISTABLE_TIMEFRAMES = frozenset({"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"})
_persist_timeframes: set[str] = set()
_registered = False

_BATCH_WAIT_SEC = 0.25
_BATCH_MAX = 50

_queue: asyncio.Queue[_QueueItem] = asyncio.Queue()
_worker: asyncio.Task | None = None


@dataclass
class _QueueItem:
    bar: OHLCVBar | None
    done: asyncio.Future | None = None


def set_persist_timeframes(timeframes: list[str]) -> None:
    """Limit DB writes to timeframes required by running auto-trading assets."""
    global _persist_timeframes
    _persist_timeframes = {tf for tf in timeframes if tf in _PERSISTABLE_TIMEFRAMES}


def get_persist_timeframes() -> set[str]:
    return set(_persist_timeframes)


def bar_to_record(bar: OHLCVBar, asset_id: int) -> OHLCVRecord:
    return OHLCVRecord(
        time=bar.bar_start,
        asset_id=asset_id,
        timeframe=bar.timeframe,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        vwap=bar.vwap,
        trade_count=bar.tick_count,
        source="alpaca",
    )


def _ensure_worker() -> None:
    global _worker
    if _worker is None or _worker.done():
        _worker = asyncio.create_task(_persist_worker(), name="bar_persist_worker")


async def _collect_batch(first: _QueueItem) -> tuple[list[OHLCVBar], list[asyncio.Future]]:
    if first.bar is None:
        futures = [first.done] if first.done is not None else []
        return [], futures

    bars: list[OHLCVBar] = [first.bar]
    futures: list[asyncio.Future] = []
    if first.done is not None:
        futures.append(first.done)

    while len(bars) < _BATCH_MAX:
        try:
            item = await asyncio.wait_for(_queue.get(), timeout=_BATCH_WAIT_SEC)
        except asyncio.TimeoutError:
            break
        if item.bar is None:
            if item.done is not None:
                futures.append(item.done)
            break
        bars.append(item.bar)
        if item.done is not None:
            futures.append(item.done)

    return bars, futures


def _resolve_futures(futures: list[asyncio.Future]) -> None:
    for future in futures:
        if not future.done():
            future.set_result(None)


async def _flush_batch(bars: list[OHLCVBar]) -> None:
    if not bars:
        return

    async with AsyncSessionLocal() as session:
        try:
            asset_ids: dict[str, int] = {}
            records: list[OHLCVRecord] = []
            for bar in bars:
                asset_id = asset_ids.get(bar.symbol)
                if asset_id is None:
                    resolved = await get_asset_id_by_symbol(session, bar.symbol)
                    if resolved is None:
                        continue
                    asset_ids[bar.symbol] = resolved
                    asset_id = resolved
                records.append(bar_to_record(bar, asset_id))

            if not records:
                return

            await bulk_insert_ohlcv(session, records)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.warning(
                "bar_persist_batch_failed",
                count=len(bars),
                error=str(exc),
            )


async def _persist_worker() -> None:
    while True:
        first = await _queue.get()
        if first.bar is None and first.done is None:
            continue

        bars, futures = await _collect_batch(first)
        try:
            await _flush_batch(bars)
        finally:
            _resolve_futures(futures)


async def flush_bar_persist_queue(timeout: float = 5.0) -> None:
    """Wait until all queued bars are written (tests and graceful shutdown)."""
    _ensure_worker()
    loop = asyncio.get_running_loop()
    done = loop.create_future()
    await _queue.put(_QueueItem(bar=None, done=done))
    await asyncio.wait_for(done, timeout=timeout)


async def persist_completed_bar(bar: OHLCVBar) -> None:
    """Queue a completed live bar for batched DB insert."""
    if bar.timeframe not in _persist_timeframes:
        return
    if bar.timeframe not in _PERSISTABLE_TIMEFRAMES:
        return

    _ensure_worker()
    await _queue.put(_QueueItem(bar=bar))


def register_bar_persistence(resampler: ResamplingEngine) -> None:
    """Attach the DB persistence callback to the resampler (once)."""
    global _registered
    if _registered:
        return
    resampler.on_bar(persist_completed_bar)
    _registered = True
