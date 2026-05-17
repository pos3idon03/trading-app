"""Routes for live trading: streaming, indicators, and signals."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from dal import live_trading_dal
from dal.market_data_dal import ensure_asset_for_live_stream, get_asset_id_by_symbol, get_ohlcv
from db import get_db
from features.live_trading.strategy_signals import MIN_BARS_REQUIRED
from dtos.live_trading_dto import (
    IndicatorSnapshotResponse,
    LiveDataUpdate,
    SignalHistoryResponse,
    StreamStartRequest,
    StreamStatusResponse,
    StrategySignalItem,
    StrategySignalsResponse,
    TradingSignalResponse,
)
from features.live_trading.indicator_engine import compute_indicators
from features.live_trading.strategy_signals import compute_strategy_signals
from features.live_trading.resampler import ResamplingEngine
from features.live_trading.signal_aggregator import (
    AISignalInput,
    RiskBounds,
    aggregate_signal,
)
from features.live_trading.stream_symbols import build_stream_plan
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


async def _await_stream_connected(
    stream,
    poll_interval: float = 0.2,
    timeout: float = 3.0,
) -> None:
    """Poll the stream status until connected or the timeout elapses."""
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
    )


async def _register_streaming_assets(session: AsyncSession, symbols: list[str]) -> None:
    """Ensure each streamed symbol has an assets row so indicators can be persisted."""
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
    plan = await build_stream_plan(session, req.symbols)
    await _register_streaming_assets(session, plan.app_symbols)

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

    stream.set_tick_handler(on_tick)
    await stream.start(plan)
    await _await_stream_connected(stream)

    status = stream.status
    return _status_to_response(status)


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

    live_close = _get_resampler().get_live_close(symbol, timeframe)
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


_WEEKLY_LOOKBACK = timedelta(weeks=104)
_DEFAULT_LOOKBACK = timedelta(days=365)


def _ohlcv_query_args(timeframe: str) -> dict:
    """Return get_ohlcv kwargs; weekly resamples stored daily bars via time_bucket."""
    if timeframe == "1w":
        return {"timeframe": "1d", "bucket_interval": timedelta(weeks=1)}
    return {"timeframe": timeframe}


def _df_rows_to_bars(df) -> list:
    """Convert a DataFrame of OHLCV rows into lightweight bar objects."""
    bars = []
    for idx, row in df.iterrows():
        bar_time = row["time"] if "time" in row.index else idx
        if hasattr(bar_time, "isoformat"):
            bar_time = bar_time.isoformat()
        else:
            bar_time = str(bar_time)
        bars.append(SimpleNamespace(
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row.get("volume", 0)),
            bar_start=bar_time,
        ))
    return bars


async def _fetch_bars_from_db(
    session: AsyncSession, symbol: str, timeframe: str,
) -> list:
    """Load historical OHLCV bars from the database for strategy evaluation."""
    asset_id = await get_asset_id_by_symbol(session, symbol)
    if asset_id is None:
        return []

    now = datetime.now(timezone.utc)
    lookback = _WEEKLY_LOOKBACK if timeframe == "1w" else _DEFAULT_LOOKBACK
    start = now - lookback

    query_args = _ohlcv_query_args(timeframe)
    df = await get_ohlcv(session, asset_id, start=start, end=now, **query_args)
    if df.empty:
        return []
    return _df_rows_to_bars(df)


async def _resolve_live_bars(
    session: AsyncSession, symbol: str, timeframe: str,
) -> list:
    """Prefer resampler bars when sufficient; otherwise use DB OHLCV (aligned with strategy-signals)."""
    bars = _get_resampler().get_bars(symbol, timeframe)
    if len(bars) >= MIN_BARS_REQUIRED:
        return bars
    db_bars = await _fetch_bars_from_db(session, symbol, timeframe)
    if len(db_bars) >= MIN_BARS_REQUIRED:
        return db_bars
    return bars


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
