from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import get_settings
from db import AsyncSessionLocal
from features.execution.deployment_timeframes import floor_to_cron_slot
from features.worker.tasks import create_and_enqueue_job
from utils.logging import get_logger

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=str(timezone.utc))
    return _scheduler


async def _enqueue_scheduled_job(job_type: str, params: dict) -> None:
    async with AsyncSessionLocal() as session:
        try:
            await create_and_enqueue_job(session, job_type, params)
        except Exception as exc:
            await session.rollback()
            logger.error("scheduler_enqueue_failed", job_type=job_type, error=str(exc))


async def _deployment_eod_job() -> None:
    scheduled_at = floor_to_cron_slot(datetime.now(timezone.utc)).isoformat()
    await _enqueue_scheduled_job(
        "deployment_market_data_refresh",
        {"timeframes": ["1d", "1w", "1mo"], "scheduled_at": scheduled_at},
    )


async def _deployment_cycle_job() -> None:
    scheduled_at = floor_to_cron_slot(datetime.now(timezone.utc)).isoformat()
    await _enqueue_scheduled_job("execution_deployment_cycle", {"scheduled_at": scheduled_at})


async def _deployment_reconciliation_job() -> None:
    await _enqueue_scheduled_job("execution_deployment_reconciliation", {})


async def _news_sentiment_enrichment_job() -> None:
    await _enqueue_scheduled_job("news_sentiment_enrichment", {})


async def _news_sentiment_job() -> None:
    await _enqueue_scheduled_job("news_sentiment", {"backfill": True})


async def _news_job() -> None:
    await _enqueue_scheduled_job("news_ingest", {"symbols": [], "limit": 50})


async def _fundamentals_job() -> None:
    await _enqueue_scheduled_job("fundamentals_ingest", {"symbols": []})


async def _fred_seed_job() -> None:
    from features.fred.macro_seed_schedule import should_enqueue_macro_seed_catalog

    async with AsyncSessionLocal() as session:
        if not await should_enqueue_macro_seed_catalog(session):
            logger.info("macro_seed_catalog_skipped", reason="recent_or_active")
            return
    await _enqueue_scheduled_job("macro_seed_catalog", {})


async def _fred_job() -> None:
    await _enqueue_scheduled_job("macro_refresh", {})


def start_scheduler() -> None:
    settings = get_settings()
    if not settings.enable_scheduler:
        return

    sched = get_scheduler()
    minutes = settings.news_interval_minutes

    sched.add_job(
        _deployment_eod_job,
        CronTrigger(hour=22, minute=0),
        id="deployment_eod_refresh",
        replace_existing=True,
    )
    sched.add_job(
        _deployment_cycle_job,
        CronTrigger(minute="*/5"),
        id="execution_deployment_cycle",
        replace_existing=True,
    )
    sched.add_job(
        _deployment_reconciliation_job,
        IntervalTrigger(minutes=settings.deployment_reconciliation_interval_minutes),
        id="execution_deployment_reconciliation",
        replace_existing=True,
    )
    sched.add_job(_news_job, IntervalTrigger(minutes=minutes), id="news_ingest", replace_existing=True)
    if settings.sentiment_enabled:
        sched.add_job(
            _news_sentiment_job,
            IntervalTrigger(minutes=settings.sentiment_interval_minutes),
            id="news_sentiment",
            replace_existing=True,
        )
    if settings.sentiment_llm_enabled:
        sched.add_job(
            _news_sentiment_enrichment_job,
            IntervalTrigger(minutes=settings.sentiment_interval_minutes),
            id="news_sentiment_enrichment",
            replace_existing=True,
        )
    sched.add_job(_fundamentals_job, CronTrigger(hour=6, minute=0), id="fundamentals_ingest", replace_existing=True)
    sched.add_job(
        _fred_seed_job,
        CronTrigger(hour=6, minute=30),
        id="fred_seed_catalog",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
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
