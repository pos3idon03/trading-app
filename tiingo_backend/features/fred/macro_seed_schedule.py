from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import job_dal

MACRO_SEED_CATALOG_JOB_TYPE = "macro_seed_catalog"


async def should_enqueue_macro_seed_catalog(session: AsyncSession) -> bool:
    settings = get_settings()
    blocked = await job_dal.has_active_or_recent_job(
        session,
        MACRO_SEED_CATALOG_JOB_TYPE,
        within_hours=settings.macro_seed_interval_hours,
    )
    return not blocked
