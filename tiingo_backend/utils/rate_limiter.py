from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import usage_dal


class RateLimitExceeded(Exception):
    pass


async def check_and_increment(session: AsyncSession, count: int = 1) -> None:
    settings = get_settings()
    summary = await usage_dal.get_usage_summary(session)
    hourly = summary.get("hourly_requests", 0) + count
    daily = summary.get("daily_requests", 0) + count
    if hourly > settings.tiingo_hourly_limit:
        raise RateLimitExceeded("Tiingo hourly request limit reached")
    if daily > settings.tiingo_daily_limit:
        raise RateLimitExceeded("Tiingo daily request limit reached")
    await usage_dal.increment_usage(session, "hourly", count)
    await usage_dal.increment_usage(session, "daily", count)
