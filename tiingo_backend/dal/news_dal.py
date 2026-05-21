from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.market_data import NewsArticle


async def bulk_insert_news(session: AsyncSession, articles: list[dict]) -> int:
    if not articles:
        return 0
    stmt = pg_insert(NewsArticle).values(articles)
    stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
    result = await session.execute(stmt)
    return result.rowcount or 0


async def list_recent_news(session: AsyncSession, limit: int = 50) -> list[dict]:
    from sqlalchemy import select

    q = (
        select(NewsArticle)
        .order_by(NewsArticle.published_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(q)).scalars().all()
    return [
        {
            "id": r.id,
            "published_at": r.published_at,
            "title": r.title,
            "url": r.url,
            "description": r.description,
            "tickers": r.tickers,
            "tags": r.tags,
        }
        for r in rows
    ]
