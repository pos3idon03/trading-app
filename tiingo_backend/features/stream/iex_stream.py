import asyncio
import json
from datetime import datetime, timezone

import websockets
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import instrument_dal, ohlcv_dal
from dtos.market_data_dto import OHLCVRecord
from db import AsyncSessionLocal
from utils.logging import get_logger

logger = get_logger(__name__)

_WS_URL = "wss://api.tiingo.com/iex"

_stream_task: asyncio.Task | None = None
_stream_running: bool = False
_subscribed_symbols: list[str] = []
_last_bar_time: dict[str, datetime] = {}


def get_stream_status() -> dict:
    return {
        "running": _stream_running,
        "symbols": list(_subscribed_symbols),
        "last_bar_time": {k: v.isoformat() for k, v in _last_bar_time.items()},
    }


async def start_stream(symbols: list[str] | None = None) -> dict:
    global _stream_task, _stream_running, _subscribed_symbols

    async with AsyncSessionLocal() as session:
        if symbols:
            _subscribed_symbols = [s.upper() for s in symbols]
        else:
            assets = await instrument_dal.list_instruments(session, active_only=True)
            _subscribed_symbols = [a["symbol"] for a in assets if a["asset_type"] != "crypto"]

    if _stream_task and not _stream_task.done():
        _stream_running = True
        return get_stream_status()

    _stream_running = True
    _stream_task = asyncio.create_task(_run_stream_loop())
    return get_stream_status()


async def stop_stream() -> dict:
    global _stream_running, _stream_task
    _stream_running = False
    if _stream_task:
        _stream_task.cancel()
        try:
            await _stream_task
        except asyncio.CancelledError:
            pass
        _stream_task = None
    return get_stream_status()


async def _run_stream_loop() -> None:
    while _stream_running:
        try:
            await _connect_and_consume()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("stream_error", error=str(exc))
            await asyncio.sleep(5)


async def _connect_and_consume() -> None:
    token = get_settings().tiingo_api_key
    if not token:
        raise RuntimeError("TIINGO_API_KEY is not configured")

    tickers = ",".join(_subscribed_symbols) if _subscribed_symbols else ""
    url = f"{_WS_URL}?tickers={tickers}&token={token}"

    async with websockets.connect(url) as ws:
        logger.info("iex_ws_connected", symbols=len(_subscribed_symbols))
        async for raw in ws:
            if not _stream_running:
                break
            await _handle_message(raw)


async def _handle_message(raw: str) -> None:
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return

    data = msg.get("data") or msg
    symbol = (data.get("ticker") or data.get("symbol") or "").upper()
    if not symbol:
        return

    price = data.get("lastSale") or data.get("close") or data.get("mid")
    if price is None:
        return

    ts_raw = data.get("timestamp") or data.get("quoteTimestamp")
    ts = datetime.now(timezone.utc)
    if ts_raw:
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    _last_bar_time[symbol] = ts

    async with AsyncSessionLocal() as session:
        inst = await instrument_dal.get_by_symbol(session, symbol)
        if not inst:
            return
        record = OHLCVRecord(
            time=ts.replace(second=0, microsecond=0),
            instrument_id=inst["id"],
            timeframe="1m",
            open=float(price),
            high=float(price),
            low=float(price),
            close=float(price),
            volume=int(data.get("volume") or 0),
            source="tiingo_iex_ws",
        )
        await ohlcv_dal.bulk_insert_ohlcv(session, [record])
        await session.commit()
