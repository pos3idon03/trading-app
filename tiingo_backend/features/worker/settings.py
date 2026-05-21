from config import get_settings
from features.worker.pool import get_redis_settings
from features.worker.tasks import run_ingestion_job


class WorkerSettings:
    """ARQ worker configuration (plain class; not imported from arq.worker)."""

    functions = [run_ingestion_job]
    redis_settings = get_redis_settings()
    max_jobs = get_settings().arq_max_jobs
    job_timeout = 3600
