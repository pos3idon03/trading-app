"""Routes for live trading: streaming, indicators, and signals."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from dal import live_trading_dal
from dal.market_data_dal import get_asset_id_by_symbol
from db import get_db
from features.live_trading.strategy_signals import MIN_BARS_REQUIRED
from dtos.live_trading_dto import (
    IndicatorSnapshotResponse,
    SignalHistoryResponse,
    StreamStartRequest,
    StreamStatusResponse,
    StrategySignalItem,
    StrategySignalsResponse,
    TradingSignalResponse,
)
from features.live_trading.bar_resolution import resolve_bars
from features.live_trading.indicator_engine import compute_indicators
from features.live_trading.live_engine import get_resampler
from features.live_trading.strategy_signals import compute_strategy_signals
from features.live_trading.stream_orchestrator import (
    attach_stream_handlers,
    ensure_resampler_timeframes,
    sync_stream_with_running_assets,
)
from features.live_trading.stream_symbols import build_stream_plan
from features.live_trading.websocket_stream import get_stream
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

_ws_clients: list[WebSocket] = []


def _get_resampler():
    """Backward-compatible alias used by scheduler and tests."""
    return get_resampler()


async def _await_stream_connected(
    stream,
    poll_interval: float = 0.2,
    timeout: float = 3.0,
) -> None:
    """Poll the stream status until connected or the timeout elapses."""
    import asyncio

    elapsed = 0.0
    while elapsed < timeout and not stream.status.connected:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval


def _status_to_response(status) -> StreamStatusResponse:
    return StreamStatusResponse(
        connected=status.connected,
        stock_connected=status.stock_connected,
        crypto_connected=status.crypto_connected,
        subscribed_symbols=status.subscribed_symbols,
        last_tick_at=status.last_tick_at,
        error=status.error,
        reconnect_count=status.reconnect_count,
        reconnecting=status.reconnecting,
        cooldown_until=status.cooldown_until,
    )


async def _register_streaming_assets(session: AsyncSession, symbols: list[str]) -> None:
    """Ensure each streamed symbol has an assets row so indicators can be persisted."""
    from dal.market_data_dal import ensure_asset_for_live_stream

    for symbol in symbols:
        try:
            await ensure_asset_for_live_stream(session, symbol)
        except Exception as exc:
            logger.warning("asset_ensure_failed", symbol=symbol, error=str(exc))


@router.post("/start", response_model=StreamStatusResponse)
async def start_stream(
    req: StreamStartRequest,
    session: AsyncSession = Depends(get_db),
):
    resampler = get_resampler()
    ensure_resampler_timeframes(req.timeframes, resampler)

    plan = await build_stream_plan(session, req.symbols)
    await _register_streaming_assets(session, plan.app_symbols)

    attach_stream_handlers(resampler, _broadcast_ws)
    stream = get_stream()
    await stream.reconcile(plan)

    return _status_to_response(stream.status)


@router.post("/stop", response_model=StreamStatusResponse)
async def stop_stream():
    stream = get_stream()
    await stream.stop()
    return _status_to_response(stream.status)


@router.get("/status", response_model=StreamStatusResponse)
async def stream_status():
    return _status_to_response(get_stream().status)


@router.get("/indicators/{symbol}", response_model=IndicatorSnapshotResponse)
async def get_indicators(
    symbol: str,
    timeframe: str = Query("1h", description="Timeframe for indicators"),
    session: AsyncSession = Depends(get_db),
):
    symbol = symbol.upper()
    bars = await _resolve_live_bars(session, symbol, timeframe)
    if len(bars) >= MIN_BARS_REQUIRED:
        return await _indicators_from_bars(session, bars, symbol, timeframe)
    return await _indicators_from_db(session, symbol, timeframe)


async def _indicators_from_bars(
    session: AsyncSession,
    bars: list,
    symbol: str,
    timeframe: str,
) -> IndicatorSnapshotResponse:
    """Compute indicators from live resampler bars; persist only when asset is registered."""
    snapshot = compute_indicators(bars, symbol, timeframe)
    if snapshot is None:
        return IndicatorSnapshotResponse(symbol=symbol, timeframe=timeframe, close_price=0.0)

    live_close = get_resampler().get_live_close(symbol, timeframe)
    if live_close is not None:
        snapshot.close_price = live_close

    asset_id = await get_asset_id_by_symbol(session, symbol)
    if asset_id is not None:
        await live_trading_dal.create_indicator(
            session,
            asset_id=asset_id,
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            rsi=snapshot.rsi,
            macd=snapshot.macd,
            macd_signal=snapshot.macd_signal,
            macd_histogram=snapshot.macd_histogram,
            bb_upper=snapshot.bb_upper,
            bb_middle=snapshot.bb_middle,
            bb_lower=snapshot.bb_lower,
            vwap=snapshot.vwap,
            close_price=snapshot.close_price,
        )
    return IndicatorSnapshotResponse(
        asset_id=asset_id,
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        close_price=snapshot.close_price,
        rsi=snapshot.rsi,
        macd=snapshot.macd,
        macd_signal=snapshot.macd_signal,
        macd_histogram=snapshot.macd_histogram,
        bb_upper=snapshot.bb_upper,
        bb_middle=snapshot.bb_middle,
        bb_lower=snapshot.bb_lower,
        vwap=snapshot.vwap,
        bb_percent=snapshot.bb_percent,
    )


async def _indicators_from_db(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
) -> IndicatorSnapshotResponse:
    """Fall back to stored indicators or raise 404 when no live bars are available."""
    asset_id = await get_asset_id_by_symbol(session, symbol)
    if asset_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{symbol}' is not registered. Ingest it first via /ingest.",
        )

    stored = await live_trading_dal.get_latest_indicator(session, symbol, timeframe)
    if stored:
        return IndicatorSnapshotResponse(
            asset_id=stored.asset_id,
            symbol=stored.symbol,
            timeframe=stored.timeframe,
            close_price=stored.close_price or 0.0,
            rsi=stored.rsi,
            macd=stored.macd,
            macd_signal=stored.macd_signal,
            macd_histogram=stored.macd_histogram,
            bb_upper=stored.bb_upper,
            bb_middle=stored.bb_middle,
            bb_lower=stored.bb_lower,
            vwap=stored.vwap,
            created_at=stored.created_at,
        )

    return IndicatorSnapshotResponse(
        asset_id=asset_id,
        symbol=symbol,
        timeframe=timeframe,
        close_price=0.0,
    )


async def _resolve_live_bars(
    session: AsyncSession, symbol: str, timeframe: str,
) -> list:
    """Merge DB history with live resampler bars."""
    return await resolve_bars(session, symbol, timeframe, get_resampler())


@router.get("/strategy-signals/{symbol}", response_model=StrategySignalsResponse)
async def get_strategy_signals(
    symbol: str,
    timeframe: str = Query("1h", description="Timeframe for strategy evaluation"),
    include_timeline: bool = Query(False, description="Include per-bar signal timeline"),
    timeline_bars: int = Query(120, ge=30, le=250, description="Bars in timeline when enabled"),
    session: AsyncSession = Depends(get_db),
):
    symbol = symbol.upper()
    bars = await _resolve_live_bars(session, symbol, timeframe)

    strategies = compute_strategy_signals(
        bars,
        symbol,
        include_timeline=include_timeline,
        timeline_bars=timeline_bars,
    )
    return StrategySignalsResponse(
        symbol=symbol,
        timeframe=timeframe,
        bar_count=len(bars),
        strategies=[
            StrategySignalItem(
                strategy=s.strategy,
                label=s.label,
                group=s.group,
                signal=s.signal,
                indicator_value=s.indicator_value,
                indicator_label=s.indicator_label,
                params=s.params,
                signal_timeline=s.signal_timeline,
            )
            for s in strategies
        ],
    )


@router.get("/signals/{symbol}", response_model=TradingSignalResponse | dict)
async def get_latest_signal(
    symbol: str,
    session: AsyncSession = Depends(get_db),
):
    sig = await live_trading_dal.get_latest_signal(session, symbol.upper())
    if sig is None:
        return {"message": f"No signal found for {symbol.upper()}"}
    return _signal_to_response(sig)


@router.get("/signals", response_model=SignalHistoryResponse)
async def get_signal_history(
    symbol: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    signals, total = await live_trading_dal.get_signal_history(
        session, symbol=symbol.upper() if symbol else None, limit=limit, offset=offset,
    )
    return SignalHistoryResponse(
        signals=[_signal_to_response(s) for s in signals],
        total=total,
    )


@router.websocket("/ws")
async def live_ws(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)


async def _broadcast_ws(data: dict) -> None:
    disconnected = []
    for ws in _ws_clients:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


def _signal_to_response(sig) -> TradingSignalResponse:
    return TradingSignalResponse(
        id=sig.id,
        asset_id=sig.asset_id,
        symbol=sig.symbol,
        timeframe=sig.timeframe,
        action=sig.action,
        confidence=sig.confidence or 0.0,
        technical_score=sig.technical_score or 0.0,
        risk_score=sig.risk_score or 0.0,
        ai_score=sig.ai_score or 0.0,
        reasoning=sig.reasoning,
        indicator_snapshot=sig.indicator_snapshot,
        risk_data=sig.risk_data,
        ai_signal=sig.ai_signal,
        created_at=sig.created_at,
    )


async def bootstrap_live_stream(session: AsyncSession) -> None:
    """Start or reconcile stream for running auto-trading assets (app startup)."""
    await sync_stream_with_running_assets(session, get_resampler(), _broadcast_ws)
