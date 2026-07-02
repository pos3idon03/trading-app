import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import job_dal, macro_brief_dal
from db import AsyncSessionLocal
from dtos.market_data_dto import (
    AssetFullIngestRequest,
    FundamentalsRunRequest,
    MacroBackfillRequest,
    NewsRunRequest,
    OHLCVBackfillRequest,
)
from dtos.sentiment_dto import NewsSentimentEnrichmentRunRequest, NewsSentimentRunRequest
from features.agents.macro_crew.context_builder import rows_fingerprint
from features.fred.macro_orchestrator import (
    backfill_alfred_releases,
    backfill_series,
    has_partial_macro_results,
    macro_job_has_observation_changes,
    refresh_enabled,
    seed_catalog,
)
from features.ingestion.asset_ingest_orchestrator import run_asset_full_ingest
from features.ingestion.fundamentals_orchestrator import run_fundamentals_ingest
from features.ingestion.news_orchestrator import run_news_ingest
from features.ingestion.ohlcv_orchestrator import has_partial_ohlcv_results, run_ohlcv_backfill
from features.market_data.overview_macro import load_macro_overview
from features.sentiment.enrichment_orchestrator import run_news_sentiment_enrichment
from features.sentiment.sentiment_orchestrator import run_news_sentiment
from utils.exceptions import JobCancelledError
from utils.logging import get_logger

logger = get_logger(__name__)


def _resolve_job_status(job_type: str, result: dict) -> str:
    if job_type == "ohlcv_backfill":
        rows = result.get("results", [])
        return "partial" if has_partial_ohlcv_results(rows) else "completed"
    if job_type == "asset_full_ingest":
        ohlcv = result.get("ohlcv", [])
        if has_partial_ohlcv_results(ohlcv):
            return "partial"
        fund_errors = result.get("fundamentals", {}).get("errors", [])
        if fund_errors:
            return "partial"
        return "completed"
    if job_type in ("macro_backfill", "macro_refresh", "macro_alfred_backfill"):
        return "partial" if has_partial_macro_results(result) else "completed"
    if job_type == "macro_seed_catalog":
        return "completed"
    if job_type == "macro_brief":
        return "completed" if result.get("available") else "failed"
    return "completed"


async def _macro_brief_fingerprint_is_stale(session: AsyncSession) -> bool:
    overview = await load_macro_overview(session, "all")
    fingerprint = rows_fingerprint(overview)
    latest = await macro_brief_dal.get_latest_brief(session)
    if latest is None:
        return True
    return latest["data_fingerprint"] != fingerprint


async def _should_enqueue_macro_brief(
    session: AsyncSession,
    result: dict,
) -> bool:
    if macro_job_has_observation_changes(result):
        return True
    return await _macro_brief_fingerprint_is_stale(session)


async def _maybe_enqueue_macro_brief(
    job_type: str,
    result: dict,
    status: str,
) -> None:
    if status not in ("completed", "partial"):
        return
    if job_type not in ("macro_backfill", "macro_refresh"):
        return
    if status == "partial" and not macro_job_has_observation_changes(result):
        return

    try:
        async with AsyncSessionLocal() as session:
            if not await _should_enqueue_macro_brief(session, result):
                return
            from features.worker.tasks import create_and_enqueue_job

            await create_and_enqueue_job(session, "macro_brief", {})
            logger.info("macro_brief_enqueued", source_job_type=job_type)
    except Exception as exc:
        logger.error("macro_brief_enqueue_failed", source_job_type=job_type, error=str(exc))


async def _job_was_cancelled(session: AsyncSession, job_id: UUID) -> bool:
    job = await job_dal.get_job(session, job_id)
    return job is not None and job["status"] == "cancelled"


async def execute_job(job_id: UUID, job_type: str, params: dict | None) -> None:
    async with AsyncSessionLocal() as session:
        try:
            if await _job_was_cancelled(session, job_id):
                return

            await job_dal.start_job(session, job_id)
            await session.commit()

            result = await _dispatch(session, job_type, params or {}, job_id)

            if await _job_was_cancelled(session, job_id):
                return

            status = _resolve_job_status(job_type, result)
            await job_dal.finish_job(session, job_id, status, result=result)
            await session.commit()
            await _maybe_enqueue_macro_brief(job_type, result, status)
        except JobCancelledError:
            await session.rollback()
            logger.info("job_cancelled", job_id=str(job_id))
        except asyncio.CancelledError:
            await session.rollback()
            logger.info("job_aborted", job_id=str(job_id))
            raise
        except Exception as exc:
            await session.rollback()
            async with AsyncSessionLocal() as err_session:
                if await _job_was_cancelled(err_session, job_id):
                    return
                await job_dal.finish_job(err_session, job_id, "failed", error=str(exc))
                await err_session.commit()
            logger.error("job_failed", job_id=str(job_id), error=str(exc))


async def _dispatch(
    session: AsyncSession,
    job_type: str,
    params: dict,
    job_id: UUID,
) -> dict:
    if job_type == "ohlcv_backfill":
        req = OHLCVBackfillRequest(**params)
        results = await run_ohlcv_backfill(session, req, job_id=job_id)
        return {"results": results}
    if job_type == "asset_full_ingest":
        req = AssetFullIngestRequest(**params)
        return await run_asset_full_ingest(session, req.symbol, job_id=job_id)
    if job_type == "news_ingest":
        req = NewsRunRequest(**params)
        return await run_news_ingest(session, req.symbols, req.limit)
    if job_type == "news_sentiment":
        req = NewsSentimentRunRequest(**params)
        return await run_news_sentiment(
            session,
            batch_size=req.batch_size,
            backfill=req.backfill,
        )
    if job_type == "news_sentiment_enrichment":
        req = NewsSentimentEnrichmentRunRequest(**params)
        return await run_news_sentiment_enrichment(
            session,
            batch_size=req.batch_size,
        )
    if job_type == "fundamentals_ingest":
        req = FundamentalsRunRequest(**params)
        return await run_fundamentals_ingest(session, req.symbols)
    if job_type == "macro_seed_catalog":
        count = await seed_catalog(session)
        return {"seeded": count}
    if job_type == "macro_backfill":
        req = MacroBackfillRequest(**params)
        return await backfill_series(session, req.series_ids, job_id=job_id)
    if job_type == "macro_alfred_backfill":
        req = MacroBackfillRequest(**params)
        return await backfill_alfred_releases(session, req.series_ids, job_id=job_id)
    if job_type == "macro_refresh":
        return await refresh_enabled(session, job_id=job_id)
    if job_type == "macro_brief":
        from features.agents.macro_crew.macro_crew_orchestrator import (
            generate_and_store_macro_brief,
        )

        return await generate_and_store_macro_brief(session, for_job=True)
    if job_type.startswith("ml_"):
        from features.ml.job_runner import execute_ml_job

        return await execute_ml_job(session, job_type, params, job_id=job_id)
    if job_type.startswith("foundation_"):
        from features.foundation.job_runner import execute_foundation_job

        return await execute_foundation_job(session, job_type, params, job_id=job_id)
    if job_type.startswith("execution_"):
        from features.execution.job_runner import execute_execution_job

        return await execute_execution_job(session, job_type, params, job_id=job_id)
    if job_type == "deployment_market_data_refresh":
        from features.execution.job_runner import execute_deployment_data_job

        return await execute_deployment_data_job(session, job_type, params)
    raise ValueError(f"Unknown job type: {job_type}")
