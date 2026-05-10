"""Routes for live trading: streaming, indicators, and signals."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from dal import live_trading_dal
from dal.market_data_dal import get_asset_id_by_symbol
from db import get_db
from dtos.live_trading_dto import (
    IndicatorSnapshotResponse,
    LiveDataUpdate,
    SignalHistoryResponse,
    StreamStartRequest,
    StreamStatusResponse,
    TradingSignalResponse,
)
from features.live_trading.indicator_engine import compute_indicators
from features.live_trading.resampler import ResamplingEngine
from features.live_trading.signal_aggregator import (
    AISignalInput,
    RiskBounds,
    aggregate_signal,
)
from features.live_trading.websocket_stream import TickData, get_stream
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

_resampler: ResamplingEngine | None = None
_ws_clients: list[WebSocket] = []


def _get_resampler() -> ResamplingEngine:
    global _resampler
    if _resampler is None:
        _resampler = ResamplingEngine()
    return _resampler


@router.post("/start", response_model=StreamStatusResponse)
async def start_stream(req: StreamStartRequest):
    stream = get_stream()
    resampler = _get_resampler()

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
        await _broadcast_ws({
            "event_type": "tick",
            "symbol": tick.symbol,
            "data": {
                "price": tick.price,
                "volume": tick.volume,
                "vwap": tick.vwap,
            },
            "timestamp": tick.timestamp.isoformat(),
        })

    stream.on_tick(on_tick)
    await stream.start(req.symbols)

    status = stream.status
    return StreamStatusResponse(
        connected=status.connected,
        subscribed_symbols=status.subscribed_symbols,
        last_tick_at=status.last_tick_at,
        error=status.error,
        reconnect_count=status.reconnect_count,
    )


@router.post("/stop", response_model=StreamStatusResponse)
async def stop_stream():
    stream = get_stream()
    await stream.stop()
    status = stream.status
    return StreamStatusResponse(
        connected=status.connected,
        subscribed_symbols=status.subscribed_symbols,
        last_tick_at=status.last_tick_at,
        error=status.error,
        reconnect_count=status.reconnect_count,
    )


@router.get("/status", response_model=StreamStatusResponse)
async def stream_status():
    status = get_stream().status
    return StreamStatusResponse(
        connected=status.connected,
        subscribed_symbols=status.subscribed_symbols,
        last_tick_at=status.last_tick_at,
        error=status.error,
        reconnect_count=status.reconnect_count,
    )


@router.get("/indicators/{symbol}", response_model=IndicatorSnapshotResponse)
async def get_indicators(
    symbol: str,
    timeframe: str = Query("1h", description="Timeframe for indicators"),
    session: AsyncSession = Depends(get_db),
):
    symbol = symbol.upper()
    asset_id = await get_asset_id_by_symbol(session, symbol)
    if asset_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{symbol}' is not registered. Ingest it first via /ingest.",
        )

    resampler = _get_resampler()
    bars = resampler.get_bars(symbol, timeframe)

    if bars:
        snapshot = compute_indicators(bars, symbol, timeframe)
        if snapshot is not None:
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
