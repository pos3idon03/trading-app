from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from dal import fundamentals_dal

_FUNDAMENTAL_LOOKBACK_DAYS = 550


async def load_fundamental_observations(
    session: AsyncSession,
    instrument_id: int,
    metric_names: list[str],
    period_type: str,
    bar_start: date,
    bar_end: date,
) -> dict[str, list[dict]]:
    obs_start = bar_start - timedelta(days=_FUNDAMENTAL_LOOKBACK_DAYS)
    metric_data: dict[str, list[dict]] = {}
    for metric_name in metric_names:
        rows = await fundamentals_dal.list_fundamentals_for_symbol(
            session,
            instrument_id,
            period_type=period_type,
            metric_names=[metric_name],
            order="asc",
            limit=None,
            start=obs_start,
            end=bar_end,
        )
        metric_data[metric_name] = rows
    return metric_data
