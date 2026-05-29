from datetime import timedelta

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from features.sentiment.text_preprocessor import title_fingerprint
from models.market_data import NewsArticle


async def _filter_title_duplicates(
    session: AsyncSession,
    articles: list[dict],
) -> list[dict]:
    settings = get_settings()
    window_hours = settings.news_title_dedup_hours
    if window_hours <= 0 or not articles:
        return articles

    filtered: list[dict] = []
    for article in articles:
        fingerprint = title_fingerprint(article.get("title") or "")
        article["title_fingerprint"] = fingerprint
        published_at = article["published_at"]
        window_start = published_at - timedelta(hours=window_hours)
        window_end = published_at + timedelta(hours=window_hours)
        q = (
            select(NewsArticle.id)
            .where(
                NewsArticle.title_fingerprint == fingerprint,
                NewsArticle.published_at >= window_start,
                NewsArticle.published_at <= window_end,
            )
            .limit(1)
        )
        existing = (await session.execute(q)).scalar_one_or_none()
        if existing is None:
            filtered.append(article)
    return filtered


async def bulk_insert_news(session: AsyncSession, articles: list[dict]) -> int:
    if not articles:
        return 0
    unique_articles = await _filter_title_duplicates(session, articles)
    if not unique_articles:
        return 0
    for article in unique_articles:
        article.setdefault("title_fingerprint", title_fingerprint(article.get("title") or ""))
    stmt = pg_insert(NewsArticle).values(unique_articles)
    stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
    result = await session.execute(stmt)
    return result.rowcount or 0


async def list_recent_news(
    session: AsyncSession,
    limit: int = 50,
    *,
    include_sentiment: bool = False,
    model_name: str | None = None,
    model_version: str | None = None,
) -> list[dict]:
    from config import get_settings
    from dal import news_sentiment_dal, news_sentiment_enrichment_dal
    from features.sentiment.effective_sentiment import resolve_effective_sentiment
    from sqlalchemy import select

    q = (
        select(NewsArticle)
        .order_by(NewsArticle.published_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(q)).scalars().all()
    articles = [
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
    if not include_sentiment or not articles:
        return articles

    settings = get_settings()
    resolved_name = model_name or settings.sentiment_model_name
    resolved_version = model_version or settings.sentiment_model_version
    article_ids = [article["id"] for article in articles]
    sentiment_map = await news_sentiment_dal.list_sentiment_by_article_ids(
        session,
        article_ids,
        model_name=resolved_name,
        model_version=resolved_version,
    )
    enrichment_map = await news_sentiment_enrichment_dal.list_enrichment_by_article_ids(
        session,
        article_ids,
        model_name=settings.sentiment_llm_model,
        model_version=settings.sentiment_llm_model_version,
    )
    for article in articles:
        finbert = sentiment_map.get(article["id"])
        enrichment = enrichment_map.get(article["id"])
        article["sentiment"] = (
            {**finbert, "source": "finbert"} if finbert else None
        )
        article["sentiment_refined"] = (
            {**enrichment, "source": "gemini"} if enrichment else None
        )
        effective = resolve_effective_sentiment(finbert, enrichment)
        article["effective_label"] = effective.label if effective else None
        article["effective_sentiment"] = (
            {
                "label": effective.label,
                "confidence": effective.confidence,
                "source": effective.source,
            }
            if effective
            else None
        )
    return articles
