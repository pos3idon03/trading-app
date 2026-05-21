from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import job_dal
from db import AsyncSessionLocal
from dtos.market_data_dto import (
    FundamentalsRunRequest,
    MacroBackfillRequest,
    NewsRunRequest,
    OHLCVBackfillRequest,
)
from features.fred.macro_orchestrator import backfill_series, refresh_enabled
from features.ingestion.fundamentals_orchestrator import run_fundamentals_ingest
from features.ingestion.news_orchestrator import run_news_ingest
from features.ingestion.ohlcv_orchestrator import run_ohlcv_backfill
from utils.logging import get_logger

logger = get_logger(__name__)


async def execute_job(job_id: UUID, job_type: str, params: dict | None) -> None:
    async with AsyncSessionLocal() as session:
        try:
            await job_dal.start_job(session, job_id)
            await session.commit()

            result = await _dispatch(session, job_type, params or {})
            await job_dal.finish_job(session, job_id, "completed", result=result)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            async with AsyncSessionLocal() as err_session:
                await job_dal.finish_job(err_session, job_id, "failed", error=str(exc))
                await err_session.commit()
            logger.error("job_failed", job_id=str(job_id), error=str(exc))


async def _dispatch(session: AsyncSession, job_type: str, params: dict) -> dict:
    if job_type == "ohlcv_backfill":
        req = OHLCVBackfillRequest(**params)
        return {"results": await run_ohlcv_backfill(session, req)}
    if job_type == "news_ingest":
        req = NewsRunRequest(**params)
        return await run_news_ingest(session, req.symbols, req.limit)
    if job_type == "fundamentals_ingest":
        req = FundamentalsRunRequest(**params)
        return await run_fundamentals_ingest(session, req.symbols)
    if job_type == "macro_backfill":
        req = MacroBackfillRequest(**params)
        return await backfill_series(session, req.series_ids)
    if job_type == "macro_refresh":
        return await refresh_enabled(session)
    raise ValueError(f"Unknown job type: {job_type}")
