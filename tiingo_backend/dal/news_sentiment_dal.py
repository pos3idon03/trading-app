from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.market_data import NewsArticle, NewsSentiment, NewsSentimentDaily, NewsSentimentEnrichment
from features.sentiment.effective_sentiment import effective_to_dict, resolve_effective_sentiment


def _article_row(row: NewsArticle) -> dict:
    return {
        "id": row.id,
        "published_at": row.published_at,
        "title": row.title,
        "url": row.url,
        "description": row.description,
        "tickers": row.tickers or [],
        "tags": row.tags or [],
    }


def _sentiment_row(row: NewsSentiment) -> dict:
    return {
        "label": row.label,
        "score_positive": row.score_positive,
        "score_negative": row.score_negative,
        "score_neutral": row.score_neutral,
        "confidence": row.confidence,
        "model_name": row.model_name,
        "model_version": row.model_version,
    }


async def list_pending_articles(
    session: AsyncSession,
    *,
    model_name: str,
    model_version: str,
    limit: int,
) -> list[dict]:
    scored_ids = (
        select(NewsSentiment.news_article_id)
        .where(
            NewsSentiment.model_name == model_name,
            NewsSentiment.model_version == model_version,
            NewsSentiment.error.is_(None),
        )
    )
    q = (
        select(NewsArticle)
        .where(NewsArticle.id.not_in(scored_ids))
        .order_by(NewsArticle.published_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(q)).scalars().all()
    return [_article_row(row) for row in rows]


async def count_pending_articles(
    session: AsyncSession,
    *,
    model_name: str,
    model_version: str,
) -> int:
    scored_ids = (
        select(NewsSentiment.news_article_id)
        .where(
            NewsSentiment.model_name == model_name,
            NewsSentiment.model_version == model_version,
            NewsSentiment.error.is_(None),
        )
    )
    q = select(func.count()).select_from(NewsArticle).where(NewsArticle.id.not_in(scored_ids))
    result = await session.execute(q)
    return int(result.scalar_one())


async def bulk_upsert_scores(session: AsyncSession, scores: list[dict]) -> int:
    if not scores:
        return 0
    stmt = pg_insert(NewsSentiment).values(scores)
    stmt = stmt.on_conflict_do_update(
        index_elements=["news_article_id", "model_name", "model_version"],
        set_={
            "label": stmt.excluded.label,
            "score_positive": stmt.excluded.score_positive,
            "score_negative": stmt.excluded.score_negative,
            "score_neutral": stmt.excluded.score_neutral,
            "confidence": stmt.excluded.confidence,
            "text_hash": stmt.excluded.text_hash,
            "scored_at": stmt.excluded.scored_at,
            "error": stmt.excluded.error,
        },
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def list_sentiment_by_article_ids(
    session: AsyncSession,
    article_ids: list[int],
    *,
    model_name: str,
    model_version: str,
) -> dict[int, dict]:
    if not article_ids:
        return {}
    q = select(NewsSentiment).where(
        NewsSentiment.news_article_id.in_(article_ids),
        NewsSentiment.model_name == model_name,
        NewsSentiment.model_version == model_version,
        NewsSentiment.error.is_(None),
    )
    rows = (await session.execute(q)).scalars().all()
    return {row.news_article_id: _sentiment_row(row) for row in rows}


async def upsert_daily_rollups(session: AsyncSession, rollups: list[dict]) -> int:
    if not rollups:
        return 0
    stmt = pg_insert(NewsSentimentDaily).values(rollups)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "date", "model_name", "model_version"],
        set_={
            "article_count": stmt.excluded.article_count,
            "avg_score": stmt.excluded.avg_score,
            "bullish_pct": stmt.excluded.bullish_pct,
            "bearish_pct": stmt.excluded.bearish_pct,
        },
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def list_daily_sentiment_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    model_name: str,
    model_version: str,
    start: date | None = None,
    end: date | None = None,
) -> list[dict]:
    q = (
        select(NewsSentimentDaily)
        .where(
            NewsSentimentDaily.symbol == symbol.upper(),
            NewsSentimentDaily.model_name == model_name,
            NewsSentimentDaily.model_version == model_version,
        )
        .order_by(NewsSentimentDaily.date.asc())
    )
    if start is not None:
        q = q.where(NewsSentimentDaily.date >= start)
    if end is not None:
        q = q.where(NewsSentimentDaily.date <= end)
    rows = (await session.execute(q)).scalars().all()
    return [
        {
            "symbol": row.symbol,
            "date": row.date,
            "article_count": row.article_count,
            "avg_score": row.avg_score,
            "bullish_pct": row.bullish_pct,
            "bearish_pct": row.bearish_pct,
        }
        for row in rows
    ]


async def get_daily_sentiment(
    session: AsyncSession,
    *,
    symbol: str,
    on_date: date,
    model_name: str,
    model_version: str,
) -> dict | None:
    q = select(NewsSentimentDaily).where(
        NewsSentimentDaily.symbol == symbol.upper(),
        NewsSentimentDaily.date == on_date,
        NewsSentimentDaily.model_name == model_name,
        NewsSentimentDaily.model_version == model_version,
    )
    row = (await session.execute(q)).scalar_one_or_none()
    if row is None:
        return None
    return {
        "symbol": row.symbol,
        "date": row.date,
        "article_count": row.article_count,
        "avg_score": row.avg_score,
        "bullish_pct": row.bullish_pct,
        "bearish_pct": row.bearish_pct,
    }


async def fetch_effective_articles_for_symbol_day(
    session: AsyncSession,
    *,
    symbol: str,
    day: date,
    finbert_model_name: str,
    finbert_model_version: str,
    llm_model_name: str,
    llm_model_version: str,
) -> list[dict]:
    day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    day_end = datetime.combine(day, datetime.max.time(), tzinfo=timezone.utc)
    q = (
        select(
            NewsArticle.id,
            NewsArticle.published_at,
            NewsArticle.tickers,
            NewsSentiment.label,
            NewsSentiment.score_positive,
            NewsSentiment.score_negative,
            NewsSentiment.score_neutral,
            NewsSentiment.confidence,
            NewsSentimentEnrichment.refined_label,
            NewsSentimentEnrichment.refined_confidence,
            NewsSentimentEnrichment.score_positive.label("enrich_score_positive"),
            NewsSentimentEnrichment.score_negative.label("enrich_score_negative"),
            NewsSentimentEnrichment.score_neutral.label("enrich_score_neutral"),
        )
        .join(
            NewsSentiment,
            and_(
                NewsSentiment.news_article_id == NewsArticle.id,
                NewsSentiment.model_name == finbert_model_name,
                NewsSentiment.model_version == finbert_model_version,
                NewsSentiment.error.is_(None),
            ),
        )
        .outerjoin(
            NewsSentimentEnrichment,
            and_(
                NewsSentimentEnrichment.news_article_id == NewsArticle.id,
                NewsSentimentEnrichment.model_name == llm_model_name,
                NewsSentimentEnrichment.model_version == llm_model_version,
                NewsSentimentEnrichment.error.is_(None),
            ),
        )
        .where(
            NewsArticle.published_at >= day_start,
            NewsArticle.published_at <= day_end,
            NewsArticle.tickers.any(symbol.upper()),
        )
    )
    rows = (await session.execute(q)).all()
    articles: list[dict] = []
    for row in rows:
        finbert = {
            "label": row.label,
            "score_positive": row.score_positive,
            "score_negative": row.score_negative,
            "score_neutral": row.score_neutral,
            "confidence": row.confidence,
        }
        enrichment = None
        if row.refined_label is not None:
            enrichment = {
                "refined_label": row.refined_label,
                "refined_confidence": row.refined_confidence,
                "score_positive": row.enrich_score_positive,
                "score_negative": row.enrich_score_negative,
                "score_neutral": row.enrich_score_neutral,
            }
        effective = resolve_effective_sentiment(finbert, enrichment)
        effective_dict = effective_to_dict(effective)
        if effective_dict is None:
            continue
        articles.append(
            {
                "id": row.id,
                "published_at": row.published_at,
                "tickers": row.tickers or [],
                "label": effective_dict["label"],
                "score_positive": effective_dict["score_positive"],
                "score_negative": effective_dict["score_negative"],
                "score_neutral": effective_dict["score_neutral"],
            }
        )
    return articles


async def fetch_scored_articles_for_symbol_day(
    session: AsyncSession,
    *,
    symbol: str,
    day: date,
    model_name: str,
    model_version: str,
) -> list[dict]:
    day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    day_end = datetime.combine(day, datetime.max.time(), tzinfo=timezone.utc)
    q = (
        select(
            NewsArticle.id,
            NewsArticle.published_at,
            NewsArticle.tickers,
            NewsSentiment.label,
            NewsSentiment.score_positive,
            NewsSentiment.score_negative,
            NewsSentiment.score_neutral,
        )
        .join(
            NewsSentiment,
            and_(
                NewsSentiment.news_article_id == NewsArticle.id,
                NewsSentiment.model_name == model_name,
                NewsSentiment.model_version == model_version,
                NewsSentiment.error.is_(None),
            ),
        )
        .where(
            NewsArticle.published_at >= day_start,
            NewsArticle.published_at <= day_end,
            NewsArticle.tickers.any(symbol.upper()),
        )
    )
    rows = (await session.execute(q)).all()
    return [
        {
            "id": row.id,
            "published_at": row.published_at,
            "tickers": row.tickers or [],
            "label": row.label,
            "score_positive": row.score_positive,
            "score_negative": row.score_negative,
            "score_neutral": row.score_neutral,
        }
        for row in rows
    ]


async def fetch_scored_articles_for_rollup(
    session: AsyncSession,
    *,
    article_ids: list[int],
    model_name: str,
    model_version: str,
) -> list[dict]:
    if not article_ids:
        return []
    q = (
        select(
            NewsArticle.id,
            NewsArticle.published_at,
            NewsArticle.tickers,
            NewsSentiment.label,
            NewsSentiment.score_positive,
            NewsSentiment.score_negative,
            NewsSentiment.score_neutral,
        )
        .join(
            NewsSentiment,
            and_(
                NewsSentiment.news_article_id == NewsArticle.id,
                NewsSentiment.model_name == model_name,
                NewsSentiment.model_version == model_version,
                NewsSentiment.error.is_(None),
            ),
        )
        .where(NewsArticle.id.in_(article_ids))
    )
    rows = (await session.execute(q)).all()
    return [
        {
            "id": row.id,
            "published_at": row.published_at,
            "tickers": row.tickers or [],
            "label": row.label,
            "score_positive": row.score_positive,
            "score_negative": row.score_negative,
            "score_neutral": row.score_neutral,
        }
        for row in rows
    ]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
