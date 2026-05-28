from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import job_dal
from db import AsyncSessionLocal
from dtos.market_data_dto import (
    AssetFullIngestRequest,
    FundamentalsRunRequest,
    MacroBackfillRequest,
    NewsRunRequest,
    OHLCVBackfillRequest,
)
from features.fred.macro_orchestrator import (
    backfill_alfred_releases,
    backfill_series,
    has_partial_macro_results,
    refresh_enabled,
    seed_catalog,
)
from features.ingestion.asset_ingest_orchestrator import run_asset_full_ingest
from features.ingestion.fundamentals_orchestrator import run_fundamentals_ingest
from features.ingestion.news_orchestrator import run_news_ingest
from features.ingestion.ohlcv_orchestrator import has_partial_ohlcv_results, run_ohlcv_backfill
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
    return "completed"


async def execute_job(job_id: UUID, job_type: str, params: dict | None) -> None:
    async with AsyncSessionLocal() as session:
        try:
            await job_dal.start_job(session, job_id)
            await session.commit()

            result = await _dispatch(session, job_type, params or {}, job_id)
            status = _resolve_job_status(job_type, result)
            await job_dal.finish_job(session, job_id, status, result=result)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            async with AsyncSessionLocal() as err_session:
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
    if job_type.startswith("ml_"):
        from features.ml.job_runner import execute_ml_job

        return await execute_ml_job(session, job_type, params, job_id=job_id)
    if job_type.startswith("foundation_"):
        from features.foundation.job_runner import execute_foundation_job

        return await execute_foundation_job(session, job_type, params, job_id=job_id)
    if job_type.startswith("execution_"):
        from features.execution.job_runner import execute_execution_job

        return await execute_execution_job(session, job_type, params, job_id=job_id)
    raise ValueError(f"Unknown job type: {job_type}")
