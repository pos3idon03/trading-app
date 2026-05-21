from sqlalchemy.ext.asyncio import AsyncSession

from dal import macro_dal
from features.fred import fred_client
from features.fred.catalog import SERIES_CATALOG, catalog_rows
from utils.logging import get_logger

logger = get_logger(__name__)


async def seed_catalog(session: AsyncSession) -> int:
    return await macro_dal.upsert_series_catalog(session, catalog_rows())


async def backfill_series(session: AsyncSession, series_ids: list[str]) -> dict:
    if not series_ids:
        series_ids = list(SERIES_CATALOG.keys())

    results = {}
    for sid in series_ids:
        try:
            obs = await fred_client.fetch_observations(sid)
            count = await macro_dal.bulk_insert_observations(session, obs)
            await macro_dal.set_series_enabled(session, sid, True)
            results[sid] = {"inserted": count, "status": "ok"}
        except Exception as exc:
            logger.error("fred_backfill_error", series_id=sid, error=str(exc))
            results[sid] = {"status": "error", "error": str(exc)}
    return results


async def refresh_enabled(session: AsyncSession) -> dict:
    ids = await macro_dal.get_enabled_series_ids(session)
    return await backfill_series(session, ids)
