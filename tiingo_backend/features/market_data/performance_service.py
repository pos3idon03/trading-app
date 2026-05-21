from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dal import ohlcv_dal
from features.market_data.performance import compute_performance_breakdown

_PERFORMANCE_LOOKBACK_DAYS = 400


async def load_performance(
    session: AsyncSession,
    instrument_id: int,
) -> tuple[list[dict], datetime | None]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=_PERFORMANCE_LOOKBACK_DAYS)
    bars, _ = await ohlcv_dal.get_bars(
        session,
        instrument_id,
        "1d",
        source="tiingo_eod",
        start=start,
        end=end,
        limit=_PERFORMANCE_LOOKBACK_DAYS,
    )
    if not bars:
        return compute_performance_breakdown([]), None

    periods = compute_performance_breakdown(bars)
    as_of = bars[-1]["time"]
    return periods, as_of
