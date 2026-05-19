"""Persist completed live resampler bars to the OHLCV hypertable."""
from __future__ import annotations

from dal.market_data_dal import bulk_insert_ohlcv, get_asset_id_by_symbol
from db import AsyncSessionLocal
from dtos.market_data_dto import OHLCVRecord
from features.live_trading.resampler import OHLCVBar, ResamplingEngine
from utils.logging import get_logger

logger = get_logger(__name__)

_PERSISTABLE_TIMEFRAMES = frozenset({"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"})
_persist_timeframes: set[str] = set()
_registered = False


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


async def persist_completed_bar(bar: OHLCVBar) -> None:
    """Insert a completed live bar when it matches active persist timeframes."""
    if bar.timeframe not in _persist_timeframes:
        return
    if bar.timeframe not in _PERSISTABLE_TIMEFRAMES:
        return

    async with AsyncSessionLocal() as session:
        try:
            asset_id = await get_asset_id_by_symbol(session, bar.symbol)
            if asset_id is None:
                return
            record = bar_to_record(bar, asset_id)
            await bulk_insert_ohlcv(session, [record])
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.warning(
                "bar_persist_failed",
                symbol=bar.symbol,
                timeframe=bar.timeframe,
                error=str(exc),
            )


def register_bar_persistence(resampler: ResamplingEngine) -> None:
    """Attach the DB persistence callback to the resampler (once)."""
    global _registered
    if _registered:
        return
    resampler.on_bar(persist_completed_bar)
    _registered = True
