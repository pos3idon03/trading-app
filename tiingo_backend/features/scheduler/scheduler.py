from datetime import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import get_settings
from db import AsyncSessionLocal
from dtos.market_data_dto import OHLCVBackfillRequest
from features.fred.macro_orchestrator import refresh_enabled
from features.ingestion.fundamentals_orchestrator import run_fundamentals_ingest
from features.ingestion.news_orchestrator import run_news_ingest
from features.ingestion.ohlcv_orchestrator import run_ohlcv_backfill
from features.stream import iex_stream
from utils.logging import get_logger

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=str(timezone.utc))
    return _scheduler


async def _eod_job() -> None:
    req = OHLCVBackfillRequest(
        symbols=[],
        timeframes=["1d"],
        sources=["tiingo_eod"],
    )
    async with AsyncSessionLocal() as session:
        try:
            await run_ohlcv_backfill(session, req)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("eod_job_error", error=str(exc))


async def _news_job() -> None:
    async with AsyncSessionLocal() as session:
        try:
            await run_news_ingest(session, [])
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("news_job_error", error=str(exc))


async def _fundamentals_job() -> None:
    async with AsyncSessionLocal() as session:
        try:
            await run_fundamentals_ingest(session, [])
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("fundamentals_job_error", error=str(exc))


async def _fred_job() -> None:
    async with AsyncSessionLocal() as session:
        try:
            await refresh_enabled(session)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("fred_job_error", error=str(exc))


def start_scheduler() -> None:
    settings = get_settings()
    if not settings.enable_scheduler:
        return

    sched = get_scheduler()
    minutes = settings.news_interval_minutes

    sched.add_job(_eod_job, CronTrigger(hour=22, minute=0), id="eod_incremental", replace_existing=True)
    sched.add_job(_news_job, IntervalTrigger(minutes=minutes), id="news_ingest", replace_existing=True)
    sched.add_job(_fundamentals_job, CronTrigger(hour=6, minute=0), id="fundamentals_ingest", replace_existing=True)
    sched.add_job(_fred_job, CronTrigger(hour=7, minute=0), id="fred_refresh", replace_existing=True)
    sched.start()
    logger.info("tiingo_scheduler_started")


def stop_scheduler() -> None:
    sched = get_scheduler()
    if sched.running:
        sched.shutdown(wait=False)


def list_jobs() -> list[dict]:
    sched = get_scheduler()
    return [
        {
            "id": j.id,
            "name": j.name,
            "next_run": j.next_run_time.isoformat() if j.next_run_time else None,
        }
        for j in sched.get_jobs()
    ]
