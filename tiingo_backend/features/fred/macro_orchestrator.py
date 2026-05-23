from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import job_dal, macro_dal
from features.fred import alfred_client, fred_client
from features.fred.catalog import SERIES_CATALOG, catalog_rows
from features.fred.release_date_fallback import uses_same_day_release_fallback
from utils.logging import get_logger

logger = get_logger(__name__)


async def seed_catalog(session: AsyncSession) -> int:
    return await macro_dal.upsert_series_catalog(session, catalog_rows())


async def _update_progress(
    session: AsyncSession,
    job_id: UUID | None,
    done: int,
    total: int,
) -> None:
    if job_id is None or total <= 0:
        return
    pct = min(100, int((done / total) * 100))
    await job_dal.update_job_progress(session, job_id, pct)
    await session.commit()


async def _ingest_release_dates(
    session: AsyncSession,
    series_id: str,
    *,
    fetch_alfred: bool,
) -> dict[str, int]:
    alfred_count = 0
    if fetch_alfred:
        try:
            rows = await alfred_client.fetch_initial_release_observations(series_id)
            if rows:
                alfred_count = await macro_dal.bulk_insert_observations(session, rows)
        except Exception as exc:
            logger.warning("alfred_ingest_skipped", series_id=series_id, error=str(exc))

    fallback_count = 0
    if uses_same_day_release_fallback(series_id):
        fallback_count = await macro_dal.backfill_same_day_release_dates(session, series_id)
        if fallback_count:
            logger.info(
                "release_date_same_day_fallback",
                series_id=series_id,
                updated=fallback_count,
            )
    return {"alfred": alfred_count, "fallback": fallback_count}


async def _ingest_series(session: AsyncSession, series_id: str, *, full: bool) -> dict:
    latest = None
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
    release = await _ingest_release_dates(
        session,
        series_id,
        fetch_alfred=full or latest is None,
    )
    await macro_dal.set_series_enabled(session, series_id, True)
    coverage = await macro_dal.get_release_date_coverage(session, series_id)
    return {
        "inserted": count,
        "alfred_updated": release["alfred"],
        "fallback_updated": release["fallback"],
        "release_date_coverage_pct": coverage["pct"],
    }


async def backfill_alfred_releases(
    session: AsyncSession,
    series_ids: list[str],
    job_id: UUID | None = None,
) -> dict:
    await seed_catalog(session)
    if not series_ids:
        series_ids = await macro_dal.get_enabled_series_ids(session)
    total = len(series_ids)
    results = {}
    for idx, sid in enumerate(series_ids):
        try:
            release = await _ingest_release_dates(session, sid, fetch_alfred=True)
            coverage = await macro_dal.get_release_date_coverage(session, sid)
            results[sid] = {
                "alfred_updated": release["alfred"],
                "fallback_updated": release["fallback"],
                "release_date_coverage_pct": coverage["pct"],
                "status": "ok",
            }
        except Exception as exc:
            logger.error("alfred_backfill_error", series_id=sid, error=str(exc))
            results[sid] = {"status": "error", "error": str(exc)}
        await _update_progress(session, job_id, idx + 1, total)
    return results


async def backfill_series(
    session: AsyncSession,
    series_ids: list[str],
    job_id: UUID | None = None,
) -> dict:
    await seed_catalog(session)
    if not series_ids:
        series_ids = list(SERIES_CATALOG.keys())

    total = len(series_ids)
    results = {}
    for idx, sid in enumerate(series_ids):
        try:
            row = await _ingest_series(session, sid, full=True)
            results[sid] = {**row, "status": "ok"}
        except Exception as exc:
            logger.error("fred_backfill_error", series_id=sid, error=str(exc))
            results[sid] = {"status": "error", "error": str(exc)}
        await _update_progress(session, job_id, idx + 1, total)
    return results


async def refresh_enabled(
    session: AsyncSession,
    job_id: UUID | None = None,
) -> dict:
    await seed_catalog(session)
    ids = await macro_dal.get_enabled_series_ids(session)
    total = len(ids)
    results = {}
    for idx, sid in enumerate(ids):
        try:
            row = await _ingest_series(session, sid, full=False)
            results[sid] = {**row, "status": "ok"}
        except Exception as exc:
            logger.error("fred_refresh_error", series_id=sid, error=str(exc))
            results[sid] = {"status": "error", "error": str(exc)}
        await _update_progress(session, job_id, idx + 1, total)
    return results


def has_partial_macro_results(results: dict) -> bool:
    return any(row.get("status") == "error" for row in results.values())
