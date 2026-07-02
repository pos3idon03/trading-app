import asyncio
from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import job_dal

T = TypeVar("T")


def progress_in_band(band_start: int, band_end: int, done: int, total: int) -> int:
    if total <= 0:
        return band_end
    return band_start + int((done / total) * (band_end - band_start))


async def checkpoint_ml_job(
    session: AsyncSession,
    job_id: UUID | None,
    progress: int,
) -> None:
    """Persist progress and raise JobCancelledError when the job was cancelled."""
    if job_id is None:
        return
    await job_dal.update_job_progress(session, job_id, progress)
    await session.commit()


def progress_at_fraction(progress_start: int, progress_end: int, fraction: float) -> int:
    span = progress_end - progress_start
    return progress_start + int(span * fraction)


async def run_cpu_bound_step(
    session: AsyncSession,
    job_id: UUID | None,
    fn: Callable[..., T],
    /,
    *args,
    **kwargs,
) -> T:
    """Run blocking work in a thread so ARQ abort and DB cancel can interleave."""
    if job_id is not None:
        await job_dal.ensure_job_active(session, job_id)
    return await asyncio.to_thread(fn, *args, **kwargs)
