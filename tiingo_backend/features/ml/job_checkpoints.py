from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import job_dal


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
