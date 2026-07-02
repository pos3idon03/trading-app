"""Abort queued or running ARQ tasks for ingestion jobs."""

import asyncio
from uuid import UUID

from arq.constants import default_queue_name
from arq.jobs import Job

from features.worker.pool import get_arq_pool
from features.worker.queue_routing import resolve_arq_queue_name
from utils.logging import get_logger

logger = get_logger(__name__)

_ABORT_POLL_ATTEMPTS = 5
_ABORT_POLL_DELAY_SEC = 0.4


async def abort_ingestion_arq_job(job_id: UUID, job_type: str) -> bool:
    """Abort the ARQ task tied to an ingestion job (queue or worker slot)."""
    pool = await get_arq_pool()
    queue_name = resolve_arq_queue_name(job_type) or default_queue_name
    job = Job(str(job_id), pool, _queue_name=queue_name)
    try:
        for attempt in range(_ABORT_POLL_ATTEMPTS):
            aborted = await job.abort()
            if aborted:
                logger.info(
                    "arq_job_aborted",
                    job_id=str(job_id),
                    queue=queue_name,
                    attempt=attempt + 1,
                )
                return True
            if attempt + 1 < _ABORT_POLL_ATTEMPTS:
                await asyncio.sleep(_ABORT_POLL_DELAY_SEC)
        logger.warning(
            "arq_job_abort_not_acknowledged",
            job_id=str(job_id),
            queue=queue_name,
        )
        return False
    except Exception as exc:
        logger.warning("arq_job_abort_failed", job_id=str(job_id), error=str(exc))
        return False
