"""Auto-start and reconcile Alpaca live stream for running auto-trading assets."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import ensure_asset_for_live_stream, get_asset_type_by_symbol
from dal.strategy_builder_dal import list_auto_trading_assets
from features.data_ingestion.ingest_service import ingest_tiingo_5m_for_symbol
from features.live_trading.bar_persistence import set_persist_timeframes
from features.live_trading.bar_resolution import count_db_bars
from features.live_trading.resampler import ResamplingEngine
from features.live_trading.stream_symbols import build_stream_plan
from features.live_trading.strategy_signals import MIN_BARS_REQUIRED
from features.live_trading.websocket_stream import TickData, get_stream
from utils.logging import get_logger

logger = get_logger(__name__)

TickBroadcastFn = Callable[[dict], Awaitable[None]]
INTRADAY_WARMUP_TIMEFRAMES = frozenset({"1m", "5m", "15m", "30m", "1h", "3h", "4h"})


@dataclass(frozen=True)
class StreamConfig:
    symbols: list[str]
    timeframes: list[str]


async def collect_running_stream_config(session: AsyncSession) -> StreamConfig:
    """Build symbol and timeframe sets from assets with auto-trading started."""
    rows = await list_auto_trading_assets(session)
    running = [r for r in rows if r.get("auto_trading_started")]
    symbols = sorted({str(r["symbol"]).upper() for r in running})
    timeframes = sorted({r.get("algo_timeframe", "1d") for r in running})
    return StreamConfig(symbols=symbols, timeframes=timeframes)


def ensure_resampler_timeframes(
    timeframes: list[str],
    resampler: ResamplingEngine,
) -> None:
    """Configure resampler buckets and DB persistence filters."""
    resampler.set_timeframes(timeframes)
    set_persist_timeframes(timeframes)


async def ensure_historical_warmup(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
) -> None:
    """Backfill Tiingo 5m history when DB lacks enough bars for evaluation."""
    if timeframe not in INTRADAY_WARMUP_TIMEFRAMES:
        return

    bar_count = await count_db_bars(session, symbol, timeframe)
    if bar_count >= MIN_BARS_REQUIRED:
        return

    asset_type = await get_asset_type_by_symbol(session, symbol) or "stock"
    try:
        await ingest_tiingo_5m_for_symbol(session, symbol, asset_type=asset_type)
        logger.info(
            "historical_warmup_ingested",
            symbol=symbol,
            timeframe=timeframe,
            prior_bars=bar_count,
        )
    except Exception as exc:
        logger.warning(
            "historical_warmup_failed",
            symbol=symbol,
            timeframe=timeframe,
            error=str(exc),
        )


async def _register_streaming_assets(session: AsyncSession, symbols: list[str]) -> None:
    for symbol in symbols:
        try:
            await ensure_asset_for_live_stream(session, symbol)
        except Exception as exc:
            logger.warning("asset_ensure_failed", symbol=symbol, error=str(exc))


def attach_stream_handlers(
    resampler: ResamplingEngine,
    broadcast_fn: TickBroadcastFn | None = None,
) -> None:
    """Wire Alpaca ticks into the resampler and optional WS broadcast."""

    async def on_tick(tick: TickData) -> None:
        await resampler.process_tick(
            symbol=tick.symbol,
            price=tick.price,
            volume=tick.volume,
            timestamp=tick.timestamp,
            vwap=tick.vwap,
            high=tick.high,
            low=tick.low,
        )
        if broadcast_fn is not None:
            await broadcast_fn({
                "event_type": "tick",
                "symbol": tick.symbol,
                "data": {
                    "price": tick.price,
                    "volume": tick.volume,
                    "vwap": tick.vwap,
                },
                "timestamp": tick.timestamp.isoformat(),
            })

    get_stream().set_tick_handler(on_tick)


async def sync_stream_with_running_assets(
    session: AsyncSession,
    resampler: ResamplingEngine,
    broadcast_fn: TickBroadcastFn | None = None,
) -> StreamConfig:
    """Reconcile the Alpaca stream for running auto-trading assets."""
    config = await collect_running_stream_config(session)

    if not config.symbols:
        ensure_resampler_timeframes([], resampler)
        await get_stream().stop()
        logger.info("stream_reconciled", action="stopped")
        return config

    ensure_resampler_timeframes(config.timeframes, resampler)

    for symbol in config.symbols:
        for timeframe in config.timeframes:
            await ensure_historical_warmup(session, symbol, timeframe)

    plan = await build_stream_plan(session, config.symbols)
    if not plan.entries:
        logger.warning("stream_sync_no_supported_symbols", requested=config.symbols)
        return config

    await _register_streaming_assets(session, plan.app_symbols)
    attach_stream_handlers(resampler, broadcast_fn)

    stream = get_stream()
    action = await stream.reconcile(plan)

    logger.info(
        "stream_reconciled",
        action=action,
        symbols=plan.app_symbols,
        timeframes=config.timeframes,
        connected=stream.status.connected,
        reconnecting=stream.status.reconnecting,
    )
    return config
