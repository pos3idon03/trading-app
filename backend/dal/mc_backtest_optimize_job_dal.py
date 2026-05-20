"""DAL for MC backtest optimize background jobs."""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.mc_backtest_optimize_job import McBacktestOptimizeJob
from utils.logging import get_logger

logger = get_logger(__name__)


async def create_job(
    session: AsyncSession,
    asset_id: int,
    symbol: str,
    request_dict: dict,
) -> int:
    job = McBacktestOptimizeJob(
        asset_id=asset_id,
        symbol=symbol,
        request=request_dict,
        status="pending",
    )
    session.add(job)
    await session.flush()
    return job.id


async def get_job(session: AsyncSession, job_id: int) -> Optional[McBacktestOptimizeJob]:
    return await session.get(McBacktestOptimizeJob, job_id)


async def mark_running(session: AsyncSession, job_id: int, total_steps: int) -> None:
    job = await session.get(McBacktestOptimizeJob, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")
    job.status = "running"
    job.total_steps = total_steps
    job.completed_steps = 0
    job.progress_pct = 0.0
    job.progress_message = "Starting optimization…"


async def update_progress(
    session: AsyncSession,
    job_id: int,
    completed: int,
    total: int,
    message: str,
) -> None:
    job = await session.get(McBacktestOptimizeJob, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")
    job.completed_steps = completed
    job.total_steps = total
    job.progress_pct = (completed / total * 100.0) if total > 0 else 0.0
    job.progress_message = message


async def mark_done(
    session: AsyncSession,
    job_id: int,
    result_dict: dict,
    duration_ms: int,
) -> None:
    job = await session.get(McBacktestOptimizeJob, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")
    job.status = "done"
    job.result = result_dict
    job.duration_ms = duration_ms
    job.progress_pct = 100.0
    job.progress_message = "Complete"
    if job.total_steps:
        job.completed_steps = job.total_steps


async def mark_error(
    session: AsyncSession,
    job_id: int,
    error_message: str,
    duration_ms: int,
) -> None:
    job = await session.get(McBacktestOptimizeJob, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")
    job.status = "error"
    job.error_message = error_message
    job.duration_ms = duration_ms
    job.progress_message = "Failed"
