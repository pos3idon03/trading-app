from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import news_sentiment_dal, news_sentiment_enrichment_dal
from features.sentiment.daily_aggregator import (
    build_daily_rollup,
    collect_rollup_keys,
    rollup_input_from_article,
)
from features.sentiment.effective_sentiment import effective_to_dict, resolve_effective_sentiment
from features.sentiment.gemini_analyzer import analyze_article
from utils.logging import get_logger

logger = get_logger(__name__)


def _finbert_config() -> tuple[str, str]:
    settings = get_settings()
    return settings.sentiment_model_name, settings.sentiment_model_version


def _llm_config() -> tuple[str, str]:
    settings = get_settings()
    return settings.sentiment_llm_model, settings.sentiment_llm_model_version


async def _persist_enrichment(
    session: AsyncSession,
    article: dict,
    result,
) -> dict:
    llm_model_name, llm_model_version = _llm_config()
    now = datetime.now(timezone.utc)
    row = {
        "news_article_id": article["id"],
        "provider": "gemini",
        "model_name": llm_model_name,
        "model_version": llm_model_version,
        "finbert_label": article.get("finbert_label") or "neutral",
        "refined_label": result.refined_label,
        "refined_confidence": result.refined_confidence,
        "score_positive": result.score_positive,
        "score_negative": result.score_negative,
        "score_neutral": result.score_neutral,
        "rationale": result.rationale,
        "citations": result.citations,
        "search_queries": result.search_queries,
        "raw_response": result.raw_response,
        "analyzed_at": now,
        "error": None,
    }
    await news_sentiment_enrichment_dal.bulk_upsert_enrichments(session, [row])
    return row


async def _update_daily_rollups(
    session: AsyncSession,
    rollup_inputs: list[dict],
) -> int:
    if not rollup_inputs:
        return 0

    finbert_name, finbert_version = _finbert_config()
    keys = collect_rollup_keys(
        rollup_inputs,
        model_name=finbert_name,
        model_version=finbert_version,
    )

    rollups: list[dict] = []
    for key in keys:
        articles = await news_sentiment_dal.fetch_effective_articles_for_symbol_day(
            session,
            symbol=key.symbol,
            day=key.day,
            finbert_model_name=finbert_name,
            finbert_model_version=finbert_version,
            llm_model_name=_llm_config()[0],
            llm_model_version=_llm_config()[1],
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


async def run_news_sentiment_enrichment(
    session: AsyncSession,
    *,
    batch_size: int | None = None,
) -> dict:
    settings = get_settings()
    if not settings.sentiment_llm_enabled:
        return {
            "enriched": 0,
            "failed": 0,
            "pending": 0,
            "skipped": True,
            "reason": "sentiment_llm_disabled",
        }
    if not settings.gemini_api_key:
        return {
            "enriched": 0,
            "failed": 0,
            "pending": 0,
            "skipped": True,
            "reason": "gemini_api_key_missing",
        }

    finbert_name, finbert_version = _finbert_config()
    llm_name, llm_version = _llm_config()
    limit = batch_size or settings.sentiment_llm_batch_size
    neutral_only = settings.sentiment_llm_neutral_only

    pending = await news_sentiment_enrichment_dal.count_pending_enrichment_articles(
        session,
        finbert_model_name=finbert_name,
        finbert_model_version=finbert_version,
        llm_model_name=llm_name,
        llm_model_version=llm_version,
        neutral_only=neutral_only,
    )
    if pending == 0:
        return {
            "enriched": 0,
            "failed": 0,
            "pending": 0,
            "model_name": llm_name,
            "model_version": llm_version,
        }

    articles = await news_sentiment_enrichment_dal.list_pending_enrichment_articles(
        session,
        finbert_model_name=finbert_name,
        finbert_model_version=finbert_version,
        llm_model_name=llm_name,
        llm_model_version=llm_version,
        neutral_only=neutral_only,
        limit=min(limit, pending),
    )

    enriched = 0
    failed = 0
    rollup_inputs: list[dict] = []

    for article in articles:
        try:
            result = await analyze_article(article)
            await _persist_enrichment(session, article, result)
            effective = resolve_effective_sentiment(
                {
                    "label": article.get("finbert_label"),
                    "score_positive": 0.0,
                    "score_negative": 0.0,
                    "score_neutral": 1.0,
                    "confidence": article.get("finbert_confidence") or 0.0,
                },
                {
                    "refined_label": result.refined_label,
                    "refined_confidence": result.refined_confidence,
                    "score_positive": result.score_positive,
                    "score_negative": result.score_negative,
                    "score_neutral": result.score_neutral,
                },
            )
            effective_dict = effective_to_dict(effective) or {}
            rollup_inputs.append(
                rollup_input_from_article(
                    article,
                    {
                        "label": effective_dict.get("label", result.refined_label),
                        "score_positive": effective_dict.get("score_positive", result.score_positive),
                        "score_negative": effective_dict.get("score_negative", result.score_negative),
                        "score_neutral": effective_dict.get("score_neutral", result.score_neutral),
                    },
                )
            )
            enriched += 1
        except Exception as exc:
            failed += 1
            logger.error(
                "news_sentiment_enrichment_failed",
                article_id=article["id"],
                error=str(exc),
            )
            await news_sentiment_enrichment_dal.bulk_upsert_enrichments(
                session,
                [{
                    "news_article_id": article["id"],
                    "provider": "gemini",
                    "model_name": llm_name,
                    "model_version": llm_version,
                    "finbert_label": article.get("finbert_label") or "neutral",
                    "refined_label": "neutral",
                    "refined_confidence": 0.0,
                    "score_positive": 0.0,
                    "score_negative": 0.0,
                    "score_neutral": 1.0,
                    "rationale": None,
                    "citations": [],
                    "search_queries": [],
                    "raw_response": None,
                    "analyzed_at": datetime.now(timezone.utc),
                    "error": str(exc),
                }],
            )

    await _update_daily_rollups(session, rollup_inputs)
    remaining = await news_sentiment_enrichment_dal.count_pending_enrichment_articles(
        session,
        finbert_model_name=finbert_name,
        finbert_model_version=finbert_version,
        llm_model_name=llm_name,
        llm_model_version=llm_version,
        neutral_only=neutral_only,
    )
    logger.info(
        "news_sentiment_enrichment_done",
        enriched=enriched,
        failed=failed,
        pending=remaining,
    )
    return {
        "enriched": enriched,
        "failed": failed,
        "pending": remaining,
        "model_name": llm_name,
        "model_version": llm_version,
    }


async def enqueue_news_sentiment_enrichment_if_enabled(session: AsyncSession) -> None:
    settings = get_settings()
    if not settings.sentiment_llm_enabled:
        return
    from features.worker.tasks import create_and_enqueue_job

    await create_and_enqueue_job(session, "news_sentiment_enrichment", {})
