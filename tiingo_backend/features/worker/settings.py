from config import get_settings
from features.worker.pool import get_redis_settings
from features.worker.tasks import run_ingestion_job

_JOB_TIMEOUT = 3600


class DefaultWorkerSettings:
    """ARQ worker for ingestion, execution, macro, and other light jobs."""

    functions = [run_ingestion_job]
    redis_settings = get_redis_settings()
    max_jobs = get_settings().arq_max_jobs
    job_timeout = _JOB_TIMEOUT


class HeavyWorkerSettings:
    """ARQ worker for foundation models, ML training/search, and FinBERT sentiment."""

    functions = [run_ingestion_job]
    redis_settings = get_redis_settings()
    queue_name = get_settings().arq_heavy_queue_name
    max_jobs = get_settings().arq_heavy_max_jobs
    job_timeout = _JOB_TIMEOUT


# Backward-compatible alias for `arq worker.WorkerSettings`
WorkerSettings = DefaultWorkerSettings
