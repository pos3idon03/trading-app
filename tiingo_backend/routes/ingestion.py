from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import instrument_dal, job_dal, news_dal, ohlcv_dal, usage_dal
from db import get_db
from dtos.market_data_dto import (
    AssetFullIngestRequest,
    FundamentalsRunRequest,
    IngestionStatusResponse,
    JobDTO,
    NewsRunRequest,
    OHLCVBackfillRequest,
    StreamControlRequest,
)
from features.scheduler.scheduler import list_jobs
from features.stream import iex_stream
from features.tiingo.entitlement import DOW_30_SYMBOLS
from features.worker.tasks import create_and_enqueue_job

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.get("/status", response_model=IngestionStatusResponse)
async def ingestion_status(session: AsyncSession = Depends(get_db)):
    instruments = await instrument_dal.list_instruments(session)
    active = [i for i in instruments if i.get("is_active")]
    usage = await usage_dal.get_usage_summary(session)
    settings = get_settings()
    return IngestionStatusResponse(
        scheduler_jobs=list_jobs(),
        api_usage={
            **usage,
            "hourly_limit": settings.tiingo_hourly_limit,
            "daily_limit": settings.tiingo_daily_limit,
        },
        stream_status=iex_stream.get_stream_status(),
        instrument_count=len(instruments),
        active_instrument_count=len(active),
    )


@router.post("/asset/ingest", status_code=202)
async def asset_ingest(
    body: AssetFullIngestRequest,
    session: AsyncSession = Depends(get_db),
):
    job = await create_and_enqueue_job(session, "asset_full_ingest", body.model_dump())
    return {"job_id": str(job["id"]), "status": "accepted"}


@router.post("/ohlcv/backfill", status_code=202)
async def ohlcv_backfill(
    body: OHLCVBackfillRequest,
    session: AsyncSession = Depends(get_db),
):
    job = await create_and_enqueue_job(session, "ohlcv_backfill", body.model_dump())
    return {"job_id": str(job["id"]), "status": "accepted"}


@router.get("/ohlcv/coverage/{symbol}")
async def ohlcv_coverage(
    symbol: str,
    timeframe: str = "1d",
    effective: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
):
    inst = await instrument_dal.get_by_symbol(session, symbol)
    if not inst:
        raise HTTPException(404, "Instrument not found")
    if effective:
        from features.market_data.effective_coverage import get_effective_coverage

        return await get_effective_coverage(session, inst["id"], timeframe)
    return await ohlcv_dal.get_coverage(session, inst["id"], timeframe)


@router.post("/news/run", status_code=202)
async def news_run(
    body: NewsRunRequest,
    session: AsyncSession = Depends(get_db),
):
    job = await create_and_enqueue_job(session, "news_ingest", body.model_dump())
    return {"job_id": str(job["id"]), "status": "accepted"}


@router.get("/news")
async def list_news(limit: int = 50, session: AsyncSession = Depends(get_db)):
    return {"articles": await news_dal.list_recent_news(session, limit)}


@router.post("/fundamentals/run", status_code=202)
async def fundamentals_run(
    body: FundamentalsRunRequest,
    session: AsyncSession = Depends(get_db),
):
    job = await create_and_enqueue_job(session, "fundamentals_ingest", body.model_dump())
    return {"job_id": str(job["id"]), "status": "accepted"}


@router.get("/fundamentals/entitlement")
async def fundamentals_entitlement():
    settings = get_settings()
    return {
        "tier": settings.tiingo_fundamentals_tier,
        "addon_active": settings.fundamentals_addon_active,
        "dow30_symbols": sorted(DOW_30_SYMBOLS),
    }


@router.post("/stream/start")
async def stream_start(body: StreamControlRequest):
    return await iex_stream.start_stream(body.symbols or None)


@router.post("/stream/stop")
async def stream_stop():
    return await iex_stream.stop_stream()


@router.get("/stream/status")
async def stream_status():
    return iex_stream.get_stream_status()


@router.get("/jobs", response_model=list[JobDTO])
async def list_ingestion_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    return await job_dal.list_jobs(session, limit, status=status)


@router.get("/jobs/active", response_model=list[JobDTO])
async def list_active_ingestion_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
):
    return await job_dal.list_active_jobs(session, limit)


@router.get("/jobs/{job_id}", response_model=JobDTO)
async def get_ingestion_job(job_id: UUID, session: AsyncSession = Depends(get_db)):
    job = await job_dal.get_job(session, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job
