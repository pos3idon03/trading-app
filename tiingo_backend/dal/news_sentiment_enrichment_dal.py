from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.market_data import NewsArticle, NewsSentiment, NewsSentimentEnrichment


def _enrichment_row(row: NewsSentimentEnrichment) -> dict:
    return {
        "provider": row.provider,
        "model_name": row.model_name,
        "model_version": row.model_version,
        "finbert_label": row.finbert_label,
        "refined_label": row.refined_label,
        "refined_confidence": row.refined_confidence,
        "score_positive": row.score_positive,
        "score_negative": row.score_negative,
        "score_neutral": row.score_neutral,
        "rationale": row.rationale,
        "citations": row.citations or [],
        "search_queries": row.search_queries or [],
        "analyzed_at": row.analyzed_at,
    }


async def list_pending_enrichment_articles(
    session: AsyncSession,
    *,
    finbert_model_name: str,
    finbert_model_version: str,
    llm_model_name: str,
    llm_model_version: str,
    neutral_only: bool,
    limit: int,
) -> list[dict]:
    enriched_ids = (
        select(NewsSentimentEnrichment.news_article_id)
        .where(
            NewsSentimentEnrichment.model_name == llm_model_name,
            NewsSentimentEnrichment.model_version == llm_model_version,
            NewsSentimentEnrichment.error.is_(None),
        )
    )
    q = (
        select(NewsArticle, NewsSentiment)
        .join(
            NewsSentiment,
            and_(
                NewsSentiment.news_article_id == NewsArticle.id,
                NewsSentiment.model_name == finbert_model_name,
                NewsSentiment.model_version == finbert_model_version,
                NewsSentiment.error.is_(None),
            ),
        )
        .where(NewsArticle.id.not_in(enriched_ids))
        .order_by(NewsArticle.published_at.desc())
        .limit(limit)
    )
    if neutral_only:
        q = q.where(NewsSentiment.label == "neutral")

    rows = (await session.execute(q)).all()
    return [
        {
            "id": article.id,
            "published_at": article.published_at,
            "title": article.title,
            "url": article.url,
            "description": article.description,
            "tickers": article.tickers or [],
            "tags": article.tags or [],
            "finbert_label": sentiment.label,
            "finbert_confidence": sentiment.confidence,
        }
        for article, sentiment in rows
    ]


async def count_pending_enrichment_articles(
    session: AsyncSession,
    *,
    finbert_model_name: str,
    finbert_model_version: str,
    llm_model_name: str,
    llm_model_version: str,
    neutral_only: bool,
) -> int:
    enriched_ids = (
        select(NewsSentimentEnrichment.news_article_id)
        .where(
            NewsSentimentEnrichment.model_name == llm_model_name,
            NewsSentimentEnrichment.model_version == llm_model_version,
            NewsSentimentEnrichment.error.is_(None),
        )
    )
    q = (
        select(func.count())
        .select_from(NewsArticle)
        .join(
            NewsSentiment,
            and_(
                NewsSentiment.news_article_id == NewsArticle.id,
                NewsSentiment.model_name == finbert_model_name,
                NewsSentiment.model_version == finbert_model_version,
                NewsSentiment.error.is_(None),
            ),
        )
        .where(NewsArticle.id.not_in(enriched_ids))
    )
    if neutral_only:
        q = q.where(NewsSentiment.label == "neutral")
    result = await session.execute(q)
    return int(result.scalar_one())


async def bulk_upsert_enrichments(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = pg_insert(NewsSentimentEnrichment).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["news_article_id", "model_name", "model_version"],
        set_={
            "finbert_label": stmt.excluded.finbert_label,
            "refined_label": stmt.excluded.refined_label,
            "refined_confidence": stmt.excluded.refined_confidence,
            "score_positive": stmt.excluded.score_positive,
            "score_negative": stmt.excluded.score_negative,
            "score_neutral": stmt.excluded.score_neutral,
            "rationale": stmt.excluded.rationale,
            "citations": stmt.excluded.citations,
            "search_queries": stmt.excluded.search_queries,
            "raw_response": stmt.excluded.raw_response,
            "analyzed_at": stmt.excluded.analyzed_at,
            "error": stmt.excluded.error,
        },
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def list_enrichment_by_article_ids(
    session: AsyncSession,
    article_ids: list[int],
    *,
    model_name: str,
    model_version: str,
) -> dict[int, dict]:
    if not article_ids:
        return {}
    q = select(NewsSentimentEnrichment).where(
        NewsSentimentEnrichment.news_article_id.in_(article_ids),
        NewsSentimentEnrichment.model_name == model_name,
        NewsSentimentEnrichment.model_version == model_version,
        NewsSentimentEnrichment.error.is_(None),
    )
    rows = (await session.execute(q)).scalars().all()
    return {row.news_article_id: _enrichment_row(row) for row in rows}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
