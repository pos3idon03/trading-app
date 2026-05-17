"""APScheduler-based periodic ingestion and auto-trading scheduler."""
from datetime import timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from db import AsyncSessionLocal
from dtos.market_data_dto import IngestRequest
from features.data_ingestion.ingest_service import run_ingest_job
from utils.logging import get_logger

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None

_ATHENS_TZ = "Europe/Athens"


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


async def _tiingo_5m_ingest_job() -> None:
    """Daily job: fetch and persist the latest 5-minute Tiingo bars for all active assets.

    Uses incremental ingestion — each symbol is fetched from its latest stored
    timestamp to now, so only missing bars are inserted.
    """
    from dal.market_data_dal import list_assets
    from features.data_ingestion.ingest_service import ingest_tiingo_5m_for_symbol

    async with AsyncSessionLocal() as session:
        try:
            assets = await list_assets(session)
            active_symbols = [
                a["symbol"] for a in assets if a.get("is_active", True)
            ]

            if not active_symbols:
                logger.info("tiingo_5m_job_skipped", reason="no_active_assets")
                return

            logger.info("tiingo_5m_job_starting", asset_count=len(active_symbols))
            results = []
            for asset in assets:
                if not asset.get("is_active", True):
                    continue
                symbol = asset["symbol"]
                asset_type = asset.get("asset_type") or "stock"
                try:
                    result = await ingest_tiingo_5m_for_symbol(
                        session, symbol, asset_type=asset_type
                    )
                    results.append({**result, "status": "ok"})
                except Exception as exc:
                    logger.error("tiingo_5m_symbol_error", symbol=symbol, error=str(exc))
                    results.append({"symbol": symbol, "timeframe": "5m", "status": "error"})

            await session.commit()
            logger.info("tiingo_5m_job_done", results=results)
        except Exception as exc:
            await session.rollback()
            logger.error("tiingo_5m_job_error", error=str(exc))


async def _daily_yfinance_ingest_job() -> None:
    """Daily job: fetch and persist 1d Yahoo Finance bars for all active assets.

    Uses incremental ingestion — each symbol is fetched from its latest stored
    date to now, so only missing daily bars are inserted.
    """
    from dal.market_data_dal import list_assets
    from features.data_ingestion.ingest_service import ingest_ohlcv_for_symbol

    async with AsyncSessionLocal() as session:
        try:
            assets = await list_assets(session)
            active_symbols = [
                a["symbol"] for a in assets if a.get("is_active", True)
            ]

            if not active_symbols:
                logger.info("daily_yfinance_job_skipped", reason="no_active_assets")
                return

            logger.info("daily_yfinance_job_starting", asset_count=len(active_symbols))
            results = []
            for symbol in active_symbols:
                try:
                    result = await ingest_ohlcv_for_symbol(
                        session, symbol, "1d", "yfinance", start=None, end=None
                    )
                    results.append({**result, "status": "ok"})
                except Exception as exc:
                    logger.error("daily_yfinance_symbol_error", symbol=symbol, error=str(exc))
                    results.append({"symbol": symbol, "timeframe": "1d", "status": "error"})

            await session.commit()
            logger.info("daily_yfinance_job_done", results=results)
        except Exception as exc:
            await session.rollback()
            logger.error("daily_yfinance_job_error", error=str(exc))


async def _auto_trading_evaluation_job() -> None:
    """Periodic job: evaluate all running auto-trading assets and execute orders."""
    from features.execution.auto_trading_loop import run_auto_trading_cycle

    async with AsyncSessionLocal() as session:
        try:
            results = await run_auto_trading_cycle(session)
            await session.commit()
            if results:
                logger.info("auto_trading_cycle_done", assets=len(results), results=results)
        except Exception as exc:
            await session.rollback()
            logger.error("auto_trading_cycle_error", error=str(exc))


def register_default_jobs(scheduler: AsyncIOScheduler) -> None:
    """Register default ingestion and auto-trading schedules."""
    scheduler.add_job(
        _tiingo_5m_ingest_job,
        CronTrigger(hour=12, minute=0, timezone=_ATHENS_TZ),
        id="tiingo_5m_ingest",
        name="Daily Tiingo 5m bar ingestion for active assets (12:00 Athens)",
        replace_existing=True,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        _daily_yfinance_ingest_job,
        CronTrigger(hour=12, minute=0, timezone=_ATHENS_TZ),
        id="ingest_daily",
        name="Daily Yahoo Finance 1d ingestion for active assets (12:00 Athens)",
        replace_existing=True,
        misfire_grace_time=600,
    )

    scheduler.add_job(
        _auto_trading_evaluation_job,
        IntervalTrigger(minutes=1),
        id="auto_trading_eval",
        name="Auto-trading signal evaluation and order execution",
        replace_existing=True,
        misfire_grace_time=60,
    )

    logger.info("default_scheduler_jobs_registered", job_count=len(scheduler.get_jobs()))


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
