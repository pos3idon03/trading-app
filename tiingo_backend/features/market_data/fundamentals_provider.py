import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import fundamentals_dal
from features.tiingo import fundamentals_client as tiingo_fundamentals
from features.tiingo.entitlement import is_fundamentals_entitled
from features.yfinance import fundamentals_client as yfinance_fundamentals
from utils.logging import get_logger
from utils.rate_limiter import check_and_increment

logger = get_logger(__name__)


async def _fetch_tiingo_rows(symbol: str, session: AsyncSession) -> list[dict]:
    await check_and_increment(session)
    return await tiingo_fundamentals.fetch_fundamentals_statements(symbol, as_reported=True)


async def _fetch_yfinance_rows(symbol: str) -> list[dict]:
    settings = get_settings()
    if not settings.yfinance_fundamentals_enabled:
        return []
    return await asyncio.to_thread(yfinance_fundamentals.fetch_fundamentals_statements, symbol)


async def fetch_fundamentals_rows(symbol: str, *, asset_type: str, session: AsyncSession) -> list[dict]:
    sym = symbol.upper()
    if asset_type != "stock":
        return []

    settings = get_settings()
    tiingo_rows: list[dict] = []
    if is_fundamentals_entitled(sym, settings.tiingo_fundamentals_tier):
        try:
            tiingo_rows = await _fetch_tiingo_rows(sym, session)
        except Exception as exc:
            logger.warning("tiingo_fundamentals_fetch_failed", symbol=sym, error=str(exc))

    if tiingo_rows:
        return tiingo_rows

    yfinance_rows = await _fetch_yfinance_rows(sym)
    if yfinance_rows:
        logger.info("fundamentals_yfinance_fallback", symbol=sym, metrics=len(yfinance_rows))
    return yfinance_rows


async def ensure_fundamentals_in_db(
    session: AsyncSession,
    instrument: dict,
    *,
    period_type: str | None = None,
    metric_names: list[str] | None = None,
    order: str = "desc",
    limit: int | None = 200,
) -> list[dict]:
    instrument_id = instrument["id"]
    rows = await fundamentals_dal.list_fundamentals_for_symbol(
        session,
        instrument_id,
        period_type=period_type,
        metric_names=metric_names,
        order=order,
        limit=limit,
    )
    if rows:
        return rows

    fetched = await fetch_fundamentals_rows(
        instrument["symbol"],
        asset_type=instrument.get("asset_type", "stock"),
        session=session,
    )
    if not fetched:
        return []

    payload = [{**row, "instrument_id": instrument_id} for row in fetched]
    await fundamentals_dal.bulk_insert_fundamentals(session, payload)
    return await fundamentals_dal.list_fundamentals_for_symbol(
        session,
        instrument_id,
        period_type=period_type,
        metric_names=metric_names,
        order=order,
        limit=limit,
    )
