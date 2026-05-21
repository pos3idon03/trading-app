from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import job_dal
from features.ingestion.fundamentals_orchestrator import run_fundamentals_ingest
from features.ingestion.ingest_presets import ohlcv_backfill_request
from features.ingestion.news_orchestrator import run_news_ingest
from features.ingestion.ohlcv_orchestrator import run_ohlcv_backfill
from utils.logging import get_logger

logger = get_logger(__name__)

_OHLCV_END = 70
_FUNDAMENTALS_END = 85


async def _set_progress(
    session: AsyncSession,
    job_id: UUID | None,
    progress: int,
) -> None:
    if job_id is None:
        return
    await job_dal.update_job_progress(session, job_id, progress)
    await session.commit()


async def run_asset_full_ingest(
    session: AsyncSession,
    symbol: str,
    job_id: UUID | None = None,
) -> dict:
    ohlcv_req = ohlcv_backfill_request([symbol])
    ohlcv_results = await run_ohlcv_backfill(
        session,
        ohlcv_req,
        job_id=job_id,
        progress_start=0,
        progress_end=_OHLCV_END,
    )
    await _set_progress(session, job_id, _OHLCV_END)

    fundamentals_result = await run_fundamentals_ingest(session, [symbol])
    await _set_progress(session, job_id, _FUNDAMENTALS_END)

    news_result = await run_news_ingest(session, [symbol], limit=50)
    await _set_progress(session, job_id, 100)

    return {
        "symbol": symbol,
        "ohlcv": ohlcv_results,
        "fundamentals": fundamentals_result,
        "news": news_result,
    }
