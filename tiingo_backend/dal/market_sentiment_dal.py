from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.market_data import MarketSentimentSnapshot


async def insert_snapshot(session: AsyncSession, row: dict) -> dict:
    snapshot = MarketSentimentSnapshot(**row)
    session.add(snapshot)
    await session.flush()
    return _snapshot_row(snapshot)


async def list_snapshots(
    session: AsyncSession,
    *,
    since: datetime,
    limit: int = 500,
) -> list[dict]:
    q = (
        select(MarketSentimentSnapshot)
        .where(MarketSentimentSnapshot.recorded_at >= since)
        .order_by(MarketSentimentSnapshot.recorded_at.asc())
        .limit(limit)
    )
    rows = (await session.execute(q)).scalars().all()
    return [_snapshot_row(row) for row in rows]


async def get_latest_snapshot(session: AsyncSession) -> dict | None:
    q = (
        select(MarketSentimentSnapshot)
        .order_by(MarketSentimentSnapshot.recorded_at.desc())
        .limit(1)
    )
    row = (await session.execute(q)).scalar_one_or_none()
    return _snapshot_row(row) if row else None


def _snapshot_row(row: MarketSentimentSnapshot) -> dict:
    return {
        "id": row.id,
        "recorded_at": row.recorded_at,
        "window_hours": row.window_hours,
        "score": row.score,
        "article_count": row.article_count,
        "bullish_count": row.bullish_count,
        "bearish_count": row.bearish_count,
        "neutral_count": row.neutral_count,
    }
