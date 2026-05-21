from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from dal import macro_dal
from features.fred import fred_client
from features.fred.catalog import SERIES_CATALOG, catalog_rows
from utils.logging import get_logger

logger = get_logger(__name__)


async def seed_catalog(session: AsyncSession) -> int:
    return await macro_dal.upsert_series_catalog(session, catalog_rows())


async def _ingest_series(session: AsyncSession, series_id: str, *, full: bool) -> int:
    if full:
        obs = await fred_client.fetch_all_observations(series_id)
    else:
        latest = await macro_dal.get_latest_obs_date(session, series_id)
        if latest is None:
            obs = await fred_client.fetch_all_observations(series_id)
        else:
            obs = await fred_client.fetch_observations_since(
                series_id, latest + timedelta(days=1),
            )
    count = await macro_dal.bulk_insert_observations(session, obs)
    await macro_dal.set_series_enabled(session, series_id, True)
    return count


async def backfill_series(session: AsyncSession, series_ids: list[str]) -> dict:
    if not series_ids:
        series_ids = list(SERIES_CATALOG.keys())

    results = {}
    for sid in series_ids:
        try:
            count = await _ingest_series(session, sid, full=True)
            results[sid] = {"inserted": count, "status": "ok"}
        except Exception as exc:
            logger.error("fred_backfill_error", series_id=sid, error=str(exc))
            results[sid] = {"status": "error", "error": str(exc)}
    return results


async def refresh_enabled(session: AsyncSession) -> dict:
    ids = await macro_dal.get_enabled_series_ids(session)
    results = {}
    for sid in ids:
        try:
            count = await _ingest_series(session, sid, full=False)
            results[sid] = {"inserted": count, "status": "ok"}
        except Exception as exc:
            logger.error("fred_refresh_error", series_id=sid, error=str(exc))
            results[sid] = {"status": "error", "error": str(exc)}
    return results
