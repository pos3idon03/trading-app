from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.ingestion_job import IngestionJob
from utils.exceptions import JobCancelledError
from utils.json_serialization import json_safe

_ACTIVE_STATUSES = ("pending", "running")


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


async def ensure_job_active(session: AsyncSession, job_id: UUID) -> None:
    status = (
        await session.execute(
            select(IngestionJob.status).where(IngestionJob.id == job_id)
        )
    ).scalar_one_or_none()
    if status == "cancelled":
        raise JobCancelledError()


async def update_job_progress(session: AsyncSession, job_id: UUID, progress: int) -> None:
    await ensure_job_active(session, job_id)
    await session.execute(
        update(IngestionJob).where(IngestionJob.id == job_id).values(progress=progress)
    )


async def cancel_job(session: AsyncSession, job_id: UUID) -> dict | None:
    now = datetime.now(timezone.utc)
    row = (
        await session.execute(
            update(IngestionJob)
            .where(
                IngestionJob.id == job_id,
                IngestionJob.status.in_(_ACTIVE_STATUSES),
            )
            .values(
                status="cancelled",
                error_message="Cancelled by user",
                finished_at=now,
            )
            .returning(IngestionJob)
        )
    ).scalar_one_or_none()
    return _to_dict(row) if row else None


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
            result=json_safe(result) if result is not None else None,
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
    return [_to_dict(r, include_result=False) for r in (await session.execute(q)).scalars().all()]


async def has_active_or_recent_job(
    session: AsyncSession,
    job_type: str,
    *,
    within_hours: int,
    success_statuses: tuple[str, ...] = ("completed", "partial"),
) -> bool:
    active = (
        await session.execute(
            select(IngestionJob.id)
            .where(
                IngestionJob.job_type == job_type,
                IngestionJob.status.in_(_ACTIVE_STATUSES),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if active is not None:
        return True

    cutoff = datetime.now(timezone.utc) - timedelta(hours=within_hours)
    recent = (
        await session.execute(
            select(IngestionJob.id)
            .where(
                IngestionJob.job_type == job_type,
                IngestionJob.status.in_(success_statuses),
                IngestionJob.created_at >= cutoff,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return recent is not None


async def list_active_jobs(session: AsyncSession, limit: int = 50) -> list[dict]:
    q = (
        select(IngestionJob)
        .where(IngestionJob.status.in_(("pending", "running")))
        .order_by(IngestionJob.created_at.desc())
        .limit(limit)
    )
    return [_to_dict(r, include_result=False) for r in (await session.execute(q)).scalars().all()]


def _to_dict(row: IngestionJob, *, include_result: bool = True) -> dict:
    payload = {
        "id": row.id,
        "job_type": row.job_type,
        "status": row.status,
        "progress": row.progress,
        "params": row.params,
        "error_message": row.error_message,
        "started_at": row.started_at,
        "finished_at": row.finished_at,
        "created_at": row.created_at,
    }
    if include_result:
        payload["result"] = row.result
    return payload
