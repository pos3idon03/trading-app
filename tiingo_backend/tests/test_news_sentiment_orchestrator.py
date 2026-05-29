from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.sentiment.finbert_scorer import SentimentScore
from features.sentiment.sentiment_orchestrator import run_news_sentiment


@pytest.mark.asyncio
async def test_run_news_sentiment_disabled():
    session = AsyncMock()
    with patch("features.sentiment.sentiment_orchestrator.get_settings") as mock_settings:
        mock_settings.return_value.sentiment_enabled = False
        mock_settings.return_value.sentiment_model_name = "ProsusAI/finbert"
        mock_settings.return_value.sentiment_model_version = "1"
        result = await run_news_sentiment(session)
    assert result["skipped"] is True
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_run_news_sentiment_scores_pending():
    session = AsyncMock()
    article = {
        "id": 1,
        "title": "Markets rise",
        "description": "Stocks gained.",
        "published_at": datetime(2024, 6, 1, tzinfo=timezone.utc),
        "tickers": ["AAPL"],
    }
    score = SentimentScore(
        label="positive",
        score_positive=0.8,
        score_negative=0.1,
        score_neutral=0.1,
        confidence=0.8,
    )

    with patch("features.sentiment.sentiment_orchestrator.get_settings") as mock_settings, patch(
        "features.sentiment.sentiment_orchestrator.news_sentiment_dal"
    ) as mock_dal, patch("features.sentiment.sentiment_orchestrator.get_scorer") as mock_scorer:
        mock_settings.return_value.sentiment_enabled = True
        mock_settings.return_value.sentiment_model_name = "ProsusAI/finbert"
        mock_settings.return_value.sentiment_model_version = "1"
        mock_settings.return_value.sentiment_batch_size = 16
        mock_settings.return_value.sentiment_max_text_chars = 512
        mock_dal.count_pending_articles = AsyncMock(side_effect=[1, 0])
        mock_dal.list_pending_articles = AsyncMock(return_value=[article])
        mock_dal.bulk_upsert_scores = AsyncMock(return_value=1)
        mock_dal.fetch_scored_articles_for_symbol_day = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "published_at": article["published_at"],
                    "tickers": ["AAPL"],
                    "label": "positive",
                    "score_positive": 0.8,
                    "score_negative": 0.1,
                    "score_neutral": 0.1,
                }
            ]
        )
        mock_dal.upsert_daily_rollups = AsyncMock(return_value=1)
        mock_scorer.return_value = MagicMock(return_value=[score])

        result = await run_news_sentiment(session)

    assert result["scored"] == 1
    assert result["pending"] == 0
    mock_dal.bulk_upsert_scores.assert_awaited_once()
    mock_dal.upsert_daily_rollups.assert_awaited_once()
