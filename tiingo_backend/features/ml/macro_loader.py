from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from dal import macro_dal

_MACRO_LOOKBACK_DAYS = 400


async def load_macro_observations(
    session: AsyncSession,
    series_ids: list[str],
    bar_start: date,
    bar_end: date,
) -> dict[str, list[dict]]:
    obs_start = bar_start - timedelta(days=_MACRO_LOOKBACK_DAYS)
    series_data: dict[str, list[dict]] = {}
    for series_id in series_ids:
        rows = await macro_dal.get_observations(
            session,
            series_id,
            limit=None,
            order="asc",
            start=obs_start,
            end=bar_end,
        )
        series_data[series_id] = rows
    return series_data
