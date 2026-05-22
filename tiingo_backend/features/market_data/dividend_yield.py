from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dal import ohlcv_dal
from features.tiingo import distributions_client
from utils.logging import get_logger
from utils.rate_limiter import check_and_increment

logger = get_logger(__name__)


async def _div_cash_yield(
    session: AsyncSession,
    instrument_id: int,
) -> float | None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365)
    bars, _ = await ohlcv_dal.get_bars(
        session,
        instrument_id,
        "1d",
        source="tiingo_eod",
        start=end - timedelta(days=400),
        end=end,
        limit=400,
    )
    if not bars:
        return None

    price = bars[-1]["close"]
    if price <= 0:
        return None

    div_sum = await ohlcv_dal.sum_div_cash(
        session, instrument_id, start=start, end=end,
    )
    if div_sum <= 0:
        return None
    return round(div_sum / price * 100.0, 2)


async def resolve_dividend_yield(
    session: AsyncSession,
    instrument_id: int,
    *,
    symbol: str,
    tiingo_ticker: str | None = None,
) -> float | None:
    ticker = tiingo_ticker or symbol
    try:
        await check_and_increment(session)
        api_yield = await distributions_client.fetch_distribution_yield(ticker)
        if api_yield is not None:
            return api_yield
    except Exception as exc:
        logger.warning(
            "distribution_yield_api_failed",
            symbol=symbol,
            ticker=ticker,
            error=str(exc),
        )

    return await _div_cash_yield(session, instrument_id)
