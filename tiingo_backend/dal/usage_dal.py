from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def increment_usage(
    session: AsyncSession,
    bucket_type: str,
    count: int = 1,
    bytes_estimate: int = 0,
) -> None:
    bucket_start = _bucket_start(bucket_type)
    stmt = text("""
        INSERT INTO api_usage_counters (bucket_type, bucket_start, request_count, bytes_estimate)
        VALUES (:bt, :bs, :cnt, :bytes)
        ON CONFLICT (bucket_type, bucket_start)
        DO UPDATE SET
            request_count = api_usage_counters.request_count + :cnt,
            bytes_estimate = api_usage_counters.bytes_estimate + :bytes
    """)
    await session.execute(
        stmt,
        {"bt": bucket_type, "bs": bucket_start, "cnt": count, "bytes": bytes_estimate},
    )


async def get_usage_summary(session: AsyncSession) -> dict[str, int]:
    hour_start = _bucket_start("hourly")
    day_start = _bucket_start("daily")
    q = text("""
        SELECT bucket_type, request_count
        FROM api_usage_counters
        WHERE (bucket_type = 'hourly' AND bucket_start = :hs)
           OR (bucket_type = 'daily' AND bucket_start = :ds)
    """)
    rows = await session.execute(q, {"hs": hour_start, "ds": day_start})
    summary = {"hourly_requests": 0, "daily_requests": 0}
    for row in rows:
        if row.bucket_type == "hourly":
            summary["hourly_requests"] = row.request_count
        else:
            summary["daily_requests"] = row.request_count
    return summary


def _bucket_start(bucket_type: str) -> datetime:
    now = datetime.now(timezone.utc)
    if bucket_type == "hourly":
        return now.replace(minute=0, second=0, microsecond=0)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)
