from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import job_dal
from features.worker.pool import get_arq_pool
from features.worker.queue_routing import resolve_arq_queue_name


async def run_ingestion_job(ctx: dict, job_id: str, job_type: str, params: dict | None) -> None:
    from features.ingestion.job_runner import execute_job

    await execute_job(UUID(job_id), job_type, params or {})


async def enqueue_ingestion_job(
    session: AsyncSession,
    job_id: UUID,
    job_type: str,
    params: dict | None,
) -> None:
    await session.commit()
    pool = await get_arq_pool()
    queue_name = resolve_arq_queue_name(job_type)
    kwargs: dict = {"_job_id": str(job_id)}
    if queue_name is not None:
        kwargs["_queue_name"] = queue_name
    await pool.enqueue_job(
        "run_ingestion_job",
        str(job_id),
        job_type,
        params or {},
        **kwargs,
    )


async def create_and_enqueue_job(
    session: AsyncSession,
    job_type: str,
    params: dict | None = None,
) -> dict:
    job = await job_dal.create_job(session, job_type, params)
    await enqueue_ingestion_job(session, job["id"], job_type, params)
    return job
