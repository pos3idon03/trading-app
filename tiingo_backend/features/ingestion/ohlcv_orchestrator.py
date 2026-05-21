from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import instrument_dal, job_dal, ohlcv_dal
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


_EOD_HISTORY_YEARS = 30


async def refresh_eod_corporate_actions(
    session: AsyncSession,
    symbol: str,
    *,
    years: int = _EOD_HISTORY_YEARS,
) -> dict:
    """Re-fetch EOD history and upsert div_cash / split_factor on existing bars."""
    inst = await instrument_dal.get_by_symbol(session, symbol)
    if not inst:
        return {"symbol": symbol, "status": "error", "error": "not found"}
    if inst["asset_type"] == "crypto":
        return {"symbol": symbol, "status": "skipped", "reason": "crypto"}

    iid = inst["id"]
    ticker = inst.get("tiingo_ticker") or symbol
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365 * years)

    await check_and_increment(session)
    recs = await eod_client.fetch_eod_bars(ticker, iid, start, end)
    updated = await ohlcv_dal.bulk_insert_ohlcv(session, recs)
    div_count = sum(1 for r in recs if r.div_cash > 0)
    split_count = sum(1 for r in recs if r.split_factor != 1)
    logger.info(
        "corporate_actions_refreshed",
        symbol=symbol,
        bars=len(recs),
        updated=updated,
        dividends=div_count,
        splits=split_count,
    )
    return {
        "symbol": symbol,
        "status": "ok",
        "bars_fetched": len(recs),
        "rows_touched": updated,
        "dividend_bars": div_count,
        "split_bars": split_count,
    }


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


async def _resolve_crypto_start(
    session: AsyncSession,
    instrument_id: int,
    timeframe: str,
    start_override: str | None,
    intraday_days: int,
) -> tuple[datetime, datetime | None]:
    latest = await ohlcv_dal.get_latest_timestamp(
        session, instrument_id, timeframe, "tiingo_crypto"
    )
    if latest:
        step = timedelta(days=1) if timeframe == "1d" else timedelta(minutes=1)
        return latest + step, datetime.now(timezone.utc)

    if start_override:
        start = datetime.fromisoformat(start_override).replace(tzinfo=timezone.utc)
        return start, None if timeframe == "1d" else datetime.now(timezone.utc)

    if timeframe == "1d":
        settings = get_settings()
        start = datetime.fromisoformat(settings.crypto_history_start_date).replace(
            tzinfo=timezone.utc
        )
        return start, None

    start = datetime.now(timezone.utc) - timedelta(days=intraday_days)
    return start, datetime.now(timezone.utc)


async def _backfill_crypto(
    session: AsyncSession,
    symbol: str,
    iid: int,
    ticker: str,
    timeframe: str,
    request: OHLCVBackfillRequest,
    intraday_days: int,
) -> int:
    start, end = await _resolve_crypto_start(
        session, iid, timeframe, request.start_date, intraday_days
    )
    await check_and_increment(session)
    recs = await crypto_client.fetch_crypto_bars(ticker, iid, timeframe, start, end)
    return await ohlcv_dal.bulk_insert_ohlcv(session, recs)


async def _backfill_timeframe(
    session: AsyncSession,
    symbol: str,
    iid: int,
    ticker: str,
    timeframe: str,
    request: OHLCVBackfillRequest,
    end: datetime,
    asset_type: str,
    sources: list[str],
    intraday_days: int,
) -> tuple[int, str | None]:
    use_crypto = asset_type == "crypto" and "tiingo_crypto" in sources
    try:
        if timeframe == "1d":
            if use_crypto:
                inserted = await _backfill_crypto(
                    session, symbol, iid, ticker, "1d", request, intraday_days
                )
                return inserted, None
            if "tiingo_eod" in sources:
                start = await _resolve_start(
                    session, iid, "1d", "tiingo_eod", request.start_date, years=_EOD_HISTORY_YEARS
                )
                await check_and_increment(session)
                recs = await eod_client.fetch_eod_bars(ticker, iid, start, end)
                inserted = await ohlcv_dal.bulk_insert_ohlcv(session, recs)
                return inserted, None
            return 0, None

        if use_crypto:
            inserted = await _backfill_crypto(
                session, symbol, iid, ticker, timeframe, request, intraday_days
            )
            return inserted, None
        if "tiingo_iex" in sources:
            start = await _resolve_start(
                session, iid, timeframe, "tiingo_iex", request.start_date, days=intraday_days
            )
            await check_and_increment(session)
            recs = await iex_client.fetch_iex_bars(ticker, iid, timeframe, start, end)
            inserted = await ohlcv_dal.bulk_insert_ohlcv(session, recs)
            return inserted, None
        return 0, None
    except Exception as exc:
        logger.error(
            "backfill_timeframe_error",
            symbol=symbol,
            timeframe=timeframe,
            error=str(exc),
        )
        return 0, str(exc)


async def _backfill_one(
    session: AsyncSession,
    symbol: str,
    request: OHLCVBackfillRequest,
    intraday_days: int,
) -> dict:
    inst = await instrument_dal.get_by_symbol(session, symbol)
    if not inst:
        return {"symbol": symbol, "status": "error", "error": "not found"}

    iid = inst["id"]
    ticker = inst.get("tiingo_ticker") or symbol
    end = datetime.now(timezone.utc)
    inserted = 0
    errors: list[dict] = []
    asset_type = inst["asset_type"]
    sources = _effective_sources(asset_type, request.sources)

    timeframes = list(request.timeframes)
    if "1d" in timeframes:
        other = [t for t in timeframes if t != "1d"]
        ordered = ["1d"] + other
    else:
        ordered = timeframes

    for tf in ordered:
        count, err = await _backfill_timeframe(
            session, symbol, iid, ticker, tf, request, end, asset_type, sources, intraday_days
        )
        inserted += count
        if err:
            errors.append({"timeframe": tf, "error": err})

    status = "ok" if not errors else "partial"
    result: dict = {"symbol": symbol, "inserted": inserted, "status": status}
    if errors:
        result["errors"] = errors
    return result


async def _update_progress(
    session: AsyncSession,
    job_id: UUID | None,
    progress_start: int,
    progress_end: int,
    done: int,
    total: int,
) -> None:
    if job_id is None or total <= 0:
        return
    pct = progress_start + int((done / total) * (progress_end - progress_start))
    await job_dal.update_job_progress(session, job_id, min(pct, progress_end))
    await session.commit()


async def run_ohlcv_backfill(
    session: AsyncSession,
    request: OHLCVBackfillRequest,
    job_id: UUID | None = None,
    progress_start: int = 0,
    progress_end: int = 100,
) -> list[dict]:
    settings = get_settings()
    intraday_days = settings.iex_backfill_days
    symbols = request.symbols
    if not symbols:
        assets = await instrument_dal.list_instruments(session, active_only=True)
        symbols = [a["symbol"] for a in assets]

    total = len(symbols)
    results = []
    for idx, sym in enumerate(symbols):
        try:
            results.append(await _backfill_one(session, sym, request, intraday_days))
            if request.refresh_corporate_actions:
                results[-1]["corporate_actions"] = await refresh_eod_corporate_actions(
                    session, sym,
                )
        except RateLimitExceeded as exc:
            results.append({"symbol": sym, "status": "rate_limited", "error": str(exc)})
        except Exception as exc:
            logger.error("backfill_error", symbol=sym, error=str(exc))
            results.append({"symbol": sym, "status": "error", "error": str(exc)})
        await _update_progress(session, job_id, progress_start, progress_end, idx + 1, total)
    return results


def has_partial_ohlcv_results(results: list[dict]) -> bool:
    for row in results:
        if row.get("status") in ("rate_limited", "partial", "error"):
            return True
    return False
