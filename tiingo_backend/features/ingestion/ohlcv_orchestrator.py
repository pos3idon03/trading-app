from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dal import instrument_dal, ohlcv_dal
from dtos.market_data_dto import OHLCVBackfillRequest
from features.tiingo import crypto_client, eod_client, iex_client
from utils.logging import get_logger
from utils.rate_limiter import RateLimitExceeded, check_and_increment

logger = get_logger(__name__)


def _effective_sources(asset_type: str, sources: list[str]) -> list[str]:
    effective = list(sources)
    if asset_type == "crypto" and "tiingo_crypto" not in effective:
        effective.append("tiingo_crypto")
    return effective


async def _resolve_start(
    session: AsyncSession,
    instrument_id: int,
    timeframe: str,
    source: str,
    start_override: str | None,
    years: int = 0,
    days: int = 0,
) -> datetime:
    if start_override:
        return datetime.fromisoformat(start_override).replace(tzinfo=timezone.utc)
    latest = await ohlcv_dal.get_latest_timestamp(session, instrument_id, timeframe, source)
    if latest:
        return latest + timedelta(minutes=1)
    if days:
        return datetime.now(timezone.utc) - timedelta(days=days)
    return datetime.now(timezone.utc) - timedelta(days=365 * max(years, 1))


async def _backfill_crypto(
    session: AsyncSession,
    symbol: str,
    iid: int,
    ticker: str,
    timeframe: str,
    request: OHLCVBackfillRequest,
    end: datetime,
) -> int:
    years = 30 if timeframe == "1d" else 0
    days = 90 if timeframe != "1d" else 0
    start = await _resolve_start(
        session, iid, timeframe, "tiingo_crypto", request.start_date, years=years, days=days
    )
    await check_and_increment(session)
    recs = await crypto_client.fetch_crypto_bars(ticker, iid, timeframe, start, end)
    return await ohlcv_dal.bulk_insert_ohlcv(session, recs)


async def _backfill_one(
    session: AsyncSession,
    symbol: str,
    request: OHLCVBackfillRequest,
) -> dict:
    inst = await instrument_dal.get_by_symbol(session, symbol)
    if not inst:
        return {"symbol": symbol, "status": "error", "error": "not found"}

    iid = inst["id"]
    ticker = inst.get("tiingo_ticker") or symbol
    end = datetime.now(timezone.utc)
    inserted = 0
    asset_type = inst["asset_type"]
    sources = _effective_sources(asset_type, request.sources)
    use_crypto = asset_type == "crypto" and "tiingo_crypto" in sources

    if "1d" in request.timeframes:
        if use_crypto:
            inserted += await _backfill_crypto(session, symbol, iid, ticker, "1d", request, end)
        elif "tiingo_eod" in sources:
            start = await _resolve_start(session, iid, "1d", "tiingo_eod", request.start_date, years=30)
            await check_and_increment(session)
            recs = await eod_client.fetch_eod_bars(ticker, iid, start, end)
            inserted += await ohlcv_dal.bulk_insert_ohlcv(session, recs)

    for tf in [t for t in request.timeframes if t != "1d"]:
        if use_crypto:
            inserted += await _backfill_crypto(session, symbol, iid, ticker, tf, request, end)
        elif "tiingo_iex" in sources:
            start = await _resolve_start(session, iid, tf, "tiingo_iex", request.start_date, days=90)
            await check_and_increment(session)
            recs = await iex_client.fetch_iex_bars(ticker, iid, tf, start, end)
            inserted += await ohlcv_dal.bulk_insert_ohlcv(session, recs)

    return {"symbol": symbol, "inserted": inserted, "status": "ok"}


async def run_ohlcv_backfill(session: AsyncSession, request: OHLCVBackfillRequest) -> list[dict]:
    symbols = request.symbols
    if not symbols:
        assets = await instrument_dal.list_instruments(session, active_only=True)
        symbols = [a["symbol"] for a in assets]

    results = []
    for sym in symbols:
        try:
            results.append(await _backfill_one(session, sym, request))
        except RateLimitExceeded as exc:
            results.append({"symbol": sym, "status": "rate_limited", "error": str(exc)})
        except Exception as exc:
            logger.error("backfill_error", symbol=sym, error=str(exc))
            results.append({"symbol": sym, "status": "error", "error": str(exc)})
    return results
