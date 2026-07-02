from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import news_sentiment_dal
from features.sentiment.daily_aggregator import (
    build_daily_rollup,
    collect_rollup_keys,
    prepare_scoring_text,
    rollup_input_from_article,
)
from features.sentiment.model_loader import get_scorer
from features.sentiment.market_sentiment import record_market_sentiment_snapshot
from utils.logging import get_logger

logger = get_logger(__name__)


def _model_config() -> tuple[str, str]:
    settings = get_settings()
    return settings.sentiment_model_name, settings.sentiment_model_version


async def _score_batch(
    articles: list[dict],
    *,
    max_chars: int,
) -> tuple[list[dict], list[dict], int]:
    scorer = get_scorer()
    texts: list[str] = []
    hashes: list[str] = []
    valid_articles: list[dict] = []

    for article in articles:
        text, text_hash = prepare_scoring_text(article, max_chars)
        if not text:
            continue
        texts.append(text)
        hashes.append(text_hash)
        valid_articles.append(article)

    if not texts:
        return [], [], 0

    try:
        scores = scorer(texts)
    except Exception as exc:
        logger.error("sentiment_scoring_failed", error=str(exc))
        raise

    model_name, model_version = _model_config()
    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    rollup_inputs: list[dict] = []
    failed = 0

    for article, score, text_hash in zip(valid_articles, scores, hashes):
        row = {
            "news_article_id": article["id"],
            "model_name": model_name,
            "model_version": model_version,
            "label": score.label,
            "score_positive": score.score_positive,
            "score_negative": score.score_negative,
            "score_neutral": score.score_neutral,
            "confidence": score.confidence,
            "text_hash": text_hash,
            "scored_at": now,
            "error": None,
        }
        rows.append(row)
        rollup_inputs.append(
            rollup_input_from_article(
                article,
                {
                    "label": score.label,
                    "score_positive": score.score_positive,
                    "score_negative": score.score_negative,
                    "score_neutral": score.score_neutral,
                },
            )
        )

    return rows, rollup_inputs, failed


async def _update_daily_rollups(
    session: AsyncSession,
    rollup_inputs: list[dict],
) -> int:
    if not rollup_inputs:
        return 0

    model_name, model_version = _model_config()
    keys = collect_rollup_keys(
        rollup_inputs,
        model_name=model_name,
        model_version=model_version,
    )

    rollups: list[dict] = []
    settings = get_settings()
    llm_name = settings.sentiment_llm_model
    llm_version = settings.sentiment_llm_model_version
    for key in keys:
        if settings.sentiment_llm_enabled:
            articles = await news_sentiment_dal.fetch_effective_articles_for_symbol_day(
                session,
                symbol=key.symbol,
                day=key.day,
                finbert_model_name=key.model_name,
                finbert_model_version=key.model_version,
                llm_model_name=llm_name,
                llm_model_version=llm_version,
            )
        else:
            articles = await news_sentiment_dal.fetch_scored_articles_for_symbol_day(
                session,
                symbol=key.symbol,
                day=key.day,
                model_name=key.model_name,
                model_version=key.model_version,
            )
        rollups.append(
            build_daily_rollup(
                key.symbol,
                key.day,
                articles,
                model_name=key.model_name,
                model_version=key.model_version,
            )
        )

    return await news_sentiment_dal.upsert_daily_rollups(session, rollups)


async def run_news_sentiment(
    session: AsyncSession,
    *,
    batch_size: int | None = None,
    backfill: bool = False,
) -> dict:
    settings = get_settings()
    if not settings.sentiment_enabled:
        return {
            "scored": 0,
            "failed": 0,
            "pending": 0,
            "model_name": settings.sentiment_model_name,
            "model_version": settings.sentiment_model_version,
            "skipped": True,
            "reason": "sentiment_disabled",
        }

    model_name, model_version = _model_config()
    limit = batch_size or settings.sentiment_batch_size
    pending = await news_sentiment_dal.count_pending_articles(
        session,
        model_name=model_name,
        model_version=model_version,
    )
    if pending == 0:
        snapshot = await record_market_sentiment_snapshot(session)
        return {
            "scored": 0,
            "failed": 0,
            "pending": 0,
            "model_name": model_name,
            "model_version": model_version,
            "market_sentiment": snapshot,
        }

    if not backfill:
        limit = min(limit, pending)

    articles = await news_sentiment_dal.list_pending_articles(
        session,
        model_name=model_name,
        model_version=model_version,
        limit=limit,
    )
    score_rows, rollup_inputs, failed = await _score_batch(
        articles,
        max_chars=settings.sentiment_max_text_chars,
    )
    scored = await news_sentiment_dal.bulk_upsert_scores(session, score_rows)
    await _update_daily_rollups(session, rollup_inputs)
    await _enqueue_enrichment_after_finbert(session)

    remaining = await news_sentiment_dal.count_pending_articles(
        session,
        model_name=model_name,
        model_version=model_version,
    )
    logger.info(
        "news_sentiment_done",
        scored=scored,
        failed=failed,
        pending=remaining,
        backfill=backfill,
    )
    snapshot = await record_market_sentiment_snapshot(session)
    return {
        "scored": scored,
        "failed": failed,
        "pending": remaining,
        "model_name": model_name,
        "model_version": model_version,
        "market_sentiment": snapshot,
    }


async def enqueue_news_sentiment_if_enabled(session: AsyncSession) -> None:
    settings = get_settings()
    if not settings.sentiment_enabled:
        return
    from features.worker.tasks import create_and_enqueue_job

    await create_and_enqueue_job(session, "news_sentiment", {"backfill": False})


async def _enqueue_enrichment_after_finbert(session: AsyncSession) -> None:
    from features.sentiment.enrichment_orchestrator import enqueue_news_sentiment_enrichment_if_enabled

    await enqueue_news_sentiment_enrichment_if_enabled(session)
