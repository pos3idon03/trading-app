from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import instrument_dal, market_sentiment_dal, news_sentiment_dal


def label_to_direction(label: str) -> int:
    normalized = label.lower().strip()
    if normalized == "positive":
        return 1
    if normalized == "negative":
        return -1
    return 0


def headline_contribution(label: str, confidence: float) -> float:
    clamped = max(0.0, min(1.0, float(confidence)))
    return label_to_direction(label) * clamped


def normalize_market_score(raw_sum: float, article_count: int) -> float:
    if article_count <= 0:
        return 50.0
    normalized = (raw_sum + article_count) / (2 * article_count) * 100
    return round(normalized, 1)


def aggregate_market_score(articles: list[dict]) -> dict:
    bullish = sum(1 for article in articles if article["label"] == "positive")
    bearish = sum(1 for article in articles if article["label"] == "negative")
    neutral = sum(1 for article in articles if article["label"] == "neutral")
    raw_sum = sum(
        headline_contribution(article["label"], article.get("confidence", 0.0))
        for article in articles
    )
    score = normalize_market_score(raw_sum, len(articles))
    return {
        "score": score,
        "article_count": len(articles),
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
    }


async def compute_rolling_market_score(session: AsyncSession) -> dict:
    settings = get_settings()
    window_hours = settings.market_sentiment_window_hours
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    instruments = await instrument_dal.list_instruments(session, active_only=True)
    symbols = [item["symbol"] for item in instruments]
    articles = await news_sentiment_dal.list_watchlist_scored_articles_in_window(
        session,
        symbols=symbols,
        since=since,
        finbert_model_name=settings.sentiment_model_name,
        finbert_model_version=settings.sentiment_model_version,
        llm_model_name=settings.sentiment_llm_model,
        llm_model_version=settings.sentiment_llm_model_version,
        llm_enabled=settings.sentiment_llm_enabled,
    )
    metrics = aggregate_market_score(articles)
    return {
        "window_hours": window_hours,
        **metrics,
    }


async def record_market_sentiment_snapshot(session: AsyncSession) -> dict:
    settings = get_settings()
    if not settings.sentiment_enabled:
        return {"skipped": True, "reason": "sentiment_disabled"}

    metrics = await compute_rolling_market_score(session)
    snapshot = await market_sentiment_dal.insert_snapshot(
        session,
        {
            "window_hours": metrics["window_hours"],
            "score": metrics["score"],
            "article_count": metrics["article_count"],
            "bullish_count": metrics["bullish_count"],
            "bearish_count": metrics["bearish_count"],
            "neutral_count": metrics["neutral_count"],
        },
    )
    return {"skipped": False, "snapshot": snapshot}


async def load_market_sentiment_overview(
    session: AsyncSession,
    *,
    hours: int = 168,
) -> dict:
    settings = get_settings()
    window_hours = settings.market_sentiment_window_hours
    if not settings.sentiment_enabled:
        return {
            "window_hours": window_hours,
            "current_score": 50.0,
            "current_article_count": 0,
            "points": [],
            "available": False,
            "message": "Sentiment analysis is disabled (SENTIMENT_ENABLED=false).",
        }

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    points = await market_sentiment_dal.list_snapshots(session, since=since)
    latest = points[-1] if points else None
    if latest is None:
        return {
            "window_hours": window_hours,
            "current_score": 50.0,
            "current_article_count": 0,
            "points": [],
            "available": True,
            "message": "No sentiment snapshots yet. Fetch and score news from Ingestion.",
        }

    return {
        "window_hours": window_hours,
        "current_score": latest["score"],
        "current_article_count": latest["article_count"],
        "points": points,
        "available": True,
        "message": None,
    }
