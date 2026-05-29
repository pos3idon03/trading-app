"""Route ingestion jobs to default or heavy ARQ queues."""

_HEAVY_EXACT = frozenset({"news_sentiment"})


def is_heavy_job(job_type: str) -> bool:
    if job_type in _HEAVY_EXACT:
        return True
    return job_type.startswith("foundation_") or job_type.startswith("ml_")


def resolve_arq_queue_name(job_type: str) -> str | None:
    """Return ARQ queue name for heavy jobs, or None for the default queue."""
    if is_heavy_job(job_type):
        from config import get_settings

        return get_settings().arq_heavy_queue_name
    return None
