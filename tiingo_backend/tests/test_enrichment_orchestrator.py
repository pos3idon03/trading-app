from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.sentiment.enrichment_orchestrator import run_news_sentiment_enrichment


@pytest.mark.asyncio
async def test_run_news_sentiment_enrichment_disabled():
    session = AsyncMock()
    with patch("features.sentiment.enrichment_orchestrator.get_settings") as mock_settings:
        mock_settings.return_value.sentiment_llm_enabled = False
        result = await run_news_sentiment_enrichment(session)
    assert result["skipped"] is True


@pytest.mark.asyncio
async def test_run_news_sentiment_enrichment_success():
    session = AsyncMock()
    article = {
        "id": 1,
        "title": "Grok AI model",
        "description": "New model training complete",
        "published_at": datetime(2024, 6, 1, tzinfo=timezone.utc),
        "tickers": ["GOOG"],
        "finbert_label": "neutral",
        "finbert_confidence": 0.58,
    }
    analysis = MagicMock(
        refined_label="positive",
        refined_confidence=0.7,
        score_positive=0.7,
        score_negative=0.15,
        score_neutral=0.15,
        rationale="Product momentum",
        citations=[{"title": "Source", "url": "https://example.com"}],
        search_queries=["grok ai"],
        raw_response={"parsed": {}},
    )

    with patch("features.sentiment.enrichment_orchestrator.get_settings") as mock_settings, patch(
        "features.sentiment.enrichment_orchestrator.news_sentiment_enrichment_dal"
    ) as mock_dal, patch(
        "features.sentiment.enrichment_orchestrator.news_sentiment_dal"
    ) as mock_sentiment_dal, patch(
        "features.sentiment.enrichment_orchestrator.analyze_article",
        new=AsyncMock(return_value=analysis),
    ):
        mock_settings.return_value.sentiment_llm_enabled = True
        mock_settings.return_value.gemini_api_key = "key"
        mock_settings.return_value.sentiment_llm_batch_size = 5
        mock_settings.return_value.sentiment_llm_neutral_only = True
        mock_settings.return_value.sentiment_model_name = "ProsusAI/finbert"
        mock_settings.return_value.sentiment_model_version = "1"
        mock_settings.return_value.sentiment_llm_model = "gemini-2.5-flash"
        mock_settings.return_value.sentiment_llm_model_version = "1"
        mock_dal.count_pending_enrichment_articles = AsyncMock(side_effect=[1, 0])
        mock_dal.list_pending_enrichment_articles = AsyncMock(return_value=[article])
        mock_dal.bulk_upsert_enrichments = AsyncMock(return_value=1)
        mock_sentiment_dal.fetch_effective_articles_for_symbol_day = AsyncMock(return_value=[])
        mock_sentiment_dal.upsert_daily_rollups = AsyncMock(return_value=0)

        result = await run_news_sentiment_enrichment(session)

    assert result["enriched"] == 1
    mock_dal.bulk_upsert_enrichments.assert_awaited()
