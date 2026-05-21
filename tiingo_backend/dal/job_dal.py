from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.ingestion_job import IngestionJob


async def create_job(session: AsyncSession, job_type: str, params: dict | None = None) -> dict:
    job_id = uuid4()
    now = datetime.now(timezone.utc)
    row = IngestionJob(
        id=job_id,
        job_type=job_type,
        status="pending",
        progress=0,
        params=params,
        created_at=now,
    )
    session.add(row)
    await session.flush()
    return _to_dict(row)


async def start_job(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        update(IngestionJob)
        .where(IngestionJob.id == job_id)
        .values(status="running", started_at=datetime.now(timezone.utc))
    )


async def update_job_progress(session: AsyncSession, job_id: UUID, progress: int) -> None:
    await session.execute(
        update(IngestionJob).where(IngestionJob.id == job_id).values(progress=progress)
    )


async def finish_job(
    session: AsyncSession,
    job_id: UUID,
    status: str,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    await session.execute(
        update(IngestionJob)
        .where(IngestionJob.id == job_id)
        .values(
            status=status,
            result=result,
            error_message=error,
            progress=100 if status in ("completed", "partial") else 0,
            finished_at=datetime.now(timezone.utc),
        )
    )


async def get_job(session: AsyncSession, job_id: UUID) -> dict | None:
    q = select(IngestionJob).where(IngestionJob.id == job_id)
    row = (await session.execute(q)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def list_jobs(
    session: AsyncSession,
    limit: int = 50,
    status: str | None = None,
) -> list[dict]:
    q = select(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(limit)
    if status:
        q = q.where(IngestionJob.status == status)
    return [_to_dict(r) for r in (await session.execute(q)).scalars().all()]


async def list_active_jobs(session: AsyncSession, limit: int = 50) -> list[dict]:
    q = (
        select(IngestionJob)
        .where(IngestionJob.status.in_(("pending", "running")))
        .order_by(IngestionJob.created_at.desc())
        .limit(limit)
    )
    return [_to_dict(r) for r in (await session.execute(q)).scalars().all()]


def _to_dict(row: IngestionJob) -> dict:
    return {
        "id": row.id,
        "job_type": row.job_type,
        "status": row.status,
        "progress": row.progress,
        "params": row.params,
        "result": row.result,
        "error_message": row.error_message,
        "started_at": row.started_at,
        "finished_at": row.finished_at,
        "created_at": row.created_at,
    }
