from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import job_dal, macro_dal
from features.fred import alfred_client, fred_client
from features.fred.catalog import SERIES_CATALOG, normalize_series_id, validate_series_ids, catalog_rows
from features.fred.release_date_fallback import uses_same_day_release_fallback
from config import get_settings
from utils.http_errors import format_external_api_error, redact_secrets
from utils.logging import get_logger

logger = get_logger(__name__)


def _safe_error_message(exc: BaseException, *, series_id: str) -> str:
    settings = get_settings()
    secrets = [settings.fred_api_key] if settings.fred_api_key else None
    return format_external_api_error(exc, context=f"series {series_id}", secret_values=secrets)


def _log_ingest_error(log_event: str, series_id: str, exc: BaseException) -> None:
    settings = get_settings()
    secrets = [settings.fred_api_key] if settings.fred_api_key else None
    logger.error(log_event, series_id=series_id, error=redact_secrets(str(exc), secrets))


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
            settings = get_settings()
            secrets = [settings.fred_api_key] if settings.fred_api_key else None
            logger.warning(
                "alfred_ingest_skipped",
                series_id=series_id,
                error=redact_secrets(str(exc), secrets),
            )

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
    series_id = normalize_series_id(series_id)
    if series_id not in SERIES_CATALOG:
        raise ValueError(f"Unknown FRED series id: {series_id}")
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
    else:
        series_ids = validate_series_ids(series_ids)
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
            _log_ingest_error("alfred_backfill_error", sid, exc)
            results[sid] = {"status": "error", "error": _safe_error_message(exc, series_id=sid)}
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
    else:
        series_ids = validate_series_ids(series_ids)

    total = len(series_ids)
    results = {}
    for idx, sid in enumerate(series_ids):
        try:
            row = await _ingest_series(session, sid, full=True)
            results[sid] = {**row, "status": "ok"}
        except Exception as exc:
            _log_ingest_error("fred_backfill_error", sid, exc)
            results[sid] = {"status": "error", "error": _safe_error_message(exc, series_id=sid)}
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
            _log_ingest_error("fred_refresh_error", sid, exc)
            results[sid] = {"status": "error", "error": _safe_error_message(exc, series_id=sid)}
        await _update_progress(session, job_id, idx + 1, total)
    return results


def has_partial_macro_results(results: dict) -> bool:
    return any(row.get("status") == "error" for row in results.values())


def macro_job_has_observation_changes(result: dict) -> bool:
    return any(
        isinstance(row, dict) and row.get("inserted", 0) > 0
        for row in result.values()
    )
