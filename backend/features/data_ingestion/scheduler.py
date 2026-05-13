"""APScheduler-based periodic ingestion scheduler."""
from datetime import timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from db import AsyncSessionLocal
from dtos.market_data_dto import IngestRequest
from features.data_ingestion.ingest_service import run_ingest_job
from utils.logging import get_logger

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=str(timezone.utc))
    return _scheduler


async def _scheduled_ingest_job(symbols: list[str], timeframes: list[str], provider: str) -> None:
    """Wrapper called by APScheduler — creates its own DB session."""
    request = IngestRequest(symbols=symbols, timeframes=timeframes, provider=provider)
    async with AsyncSessionLocal() as session:
        try:
            results = await run_ingest_job(session, request)
            await session.commit()
            logger.info("scheduled_ingest_done", results=results)
        except Exception as exc:
            await session.rollback()
            logger.error("scheduled_ingest_error", error=str(exc))


async def _nightly_full_ingest() -> None:
    """Midnight job: ingest daily prices for ALL assets stored in the database."""
    from dal.market_data_dal import list_assets

    async with AsyncSessionLocal() as session:
        try:
            assets = await list_assets(session)
            active_symbols = [
                a["symbol"] for a in assets if a.get("is_active", True)
            ]

            if not active_symbols:
                logger.info("nightly_ingest_skipped", reason="no_active_assets")
                return

            logger.info("nightly_ingest_starting", asset_count=len(active_symbols))
            request = IngestRequest(
                symbols=active_symbols,
                timeframes=["1d"],
                provider="yfinance",
            )
            results = await run_ingest_job(session, request)
            await session.commit()
            logger.info("nightly_ingest_done", results=results)
        except Exception as exc:
            await session.rollback()
            logger.error("nightly_ingest_error", error=str(exc))


def register_default_jobs(scheduler: AsyncIOScheduler) -> None:
    """Register default ingestion schedules (configurable via env/API in later phases)."""
    default_symbols = ["AAPL", "MSFT", "SPY", "QQQ"]

    scheduler.add_job(
        _scheduled_ingest_job,
        CronTrigger(hour="*/1", minute="5"),
        id="ingest_1h",
        name="Hourly 1h OHLCV ingestion",
        kwargs={"symbols": default_symbols, "timeframes": ["1h"], "provider": "polygon"},
        replace_existing=True,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        _scheduled_ingest_job,
        CronTrigger(hour="17", minute="30"),
        id="ingest_daily",
        name="Daily EOD ingestion",
        kwargs={"symbols": default_symbols, "timeframes": ["1d"], "provider": "yfinance"},
        replace_existing=True,
        misfire_grace_time=600,
    )

    scheduler.add_job(
        _nightly_full_ingest,
        CronTrigger(hour=0, minute=0),
        id="ingest_nightly_all_assets",
        name="Nightly full price ingestion (all DB assets)",
        replace_existing=True,
        misfire_grace_time=900,
    )

    logger.info("default_scheduler_jobs_registered", job_count=scheduler.get_jobs().__len__())


def start_scheduler() -> AsyncIOScheduler:
    scheduler = get_scheduler()
    register_default_jobs(scheduler)
    scheduler.start()
    logger.info("scheduler_started")
    return scheduler


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")


def list_jobs() -> list[dict[str, Any]]:
    scheduler = get_scheduler()
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        }
        for job in scheduler.get_jobs()
    ]
