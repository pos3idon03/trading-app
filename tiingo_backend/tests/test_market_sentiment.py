from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from features.sentiment.market_sentiment import (
    aggregate_market_score,
    compute_rolling_market_score,
    headline_contribution,
    label_to_direction,
    load_market_sentiment_overview,
    normalize_market_score,
    record_market_sentiment_snapshot,
)


def test_label_to_direction_mapping():
    assert label_to_direction("positive") == 1
    assert label_to_direction("negative") == -1
    assert label_to_direction("neutral") == 0
    assert label_to_direction("unknown") == 0


def test_headline_contribution_uses_confidence():
    assert headline_contribution("positive", 0.90) == 0.9
    assert headline_contribution("negative", 0.79) == -0.79
    assert headline_contribution("neutral", 0.51) == 0.0


def test_normalize_market_score_single_bullish_headline():
    assert normalize_market_score(0.9, 1) == 95.0


def test_normalize_market_score_all_bearish():
    assert normalize_market_score(-2.0, 2) == 0.0


def test_normalize_market_score_all_neutral():
    assert normalize_market_score(0.0, 4) == 50.0


def test_normalize_market_score_empty():
    assert normalize_market_score(0.0, 0) == 50.0


def test_aggregate_market_score_mixed_weighted():
    articles = [
        {"label": "positive", "confidence": 0.90},
        {"label": "negative", "confidence": 0.79},
        {"label": "neutral", "confidence": 0.51},
        {"label": "positive", "confidence": 0.50},
    ]
    result = aggregate_market_score(articles)
    raw_sum = 0.9 - 0.79 + 0.0 + 0.5
    assert result["score"] == normalize_market_score(raw_sum, 4)
    assert result["article_count"] == 4
    assert result["bullish_count"] == 2
    assert result["bearish_count"] == 1
    assert result["neutral_count"] == 1


@pytest.mark.asyncio
async def test_compute_rolling_market_score_uses_watchlist_and_window():
    session = AsyncMock()
    now = datetime.now(timezone.utc)
    articles = [{"id": 1, "label": "positive", "confidence": 0.9, "published_at": now, "tickers": ["AAPL"]}]

    with patch("features.sentiment.market_sentiment.get_settings") as mock_settings, patch(
        "features.sentiment.market_sentiment.instrument_dal.list_instruments",
        new=AsyncMock(return_value=[{"symbol": "AAPL"}]),
    ), patch(
        "features.sentiment.market_sentiment.news_sentiment_dal.list_watchlist_scored_articles_in_window",
        new=AsyncMock(return_value=articles),
    ) as mock_list:
        mock_settings.return_value.market_sentiment_window_hours = 24
        mock_settings.return_value.sentiment_model_name = "ProsusAI/finbert"
        mock_settings.return_value.sentiment_model_version = "1"
        mock_settings.return_value.sentiment_llm_model = "gemini-2.5-flash"
        mock_settings.return_value.sentiment_llm_model_version = "1"
        mock_settings.return_value.sentiment_llm_enabled = False

        result = await compute_rolling_market_score(session)

    assert result["score"] == 95.0
    assert result["article_count"] == 1
    assert mock_list.await_count == 1
    since = mock_list.await_args.kwargs["since"]
    assert since <= datetime.now(timezone.utc) - timedelta(hours=23, minutes=59)


@pytest.mark.asyncio
async def test_record_market_sentiment_snapshot_skips_when_disabled():
    session = AsyncMock()
    with patch("features.sentiment.market_sentiment.get_settings") as mock_settings:
        mock_settings.return_value.sentiment_enabled = False
        result = await record_market_sentiment_snapshot(session)
    assert result["skipped"] is True
    assert result["reason"] == "sentiment_disabled"


@pytest.mark.asyncio
async def test_record_market_sentiment_snapshot_persists_row():
    session = AsyncMock()
    snapshot = {
        "id": 1,
        "recorded_at": datetime.now(timezone.utc),
        "window_hours": 24,
        "score": 72.5,
        "article_count": 5,
        "bullish_count": 4,
        "bearish_count": 1,
        "neutral_count": 0,
    }

    with patch("features.sentiment.market_sentiment.get_settings") as mock_settings, patch(
        "features.sentiment.market_sentiment.compute_rolling_market_score",
        new=AsyncMock(
            return_value={
                "window_hours": 24,
                "score": 72.5,
                "article_count": 5,
                "bullish_count": 4,
                "bearish_count": 1,
                "neutral_count": 0,
            }
        ),
    ), patch(
        "features.sentiment.market_sentiment.market_sentiment_dal.insert_snapshot",
        new=AsyncMock(return_value=snapshot),
    ) as mock_insert:
        mock_settings.return_value.sentiment_enabled = True
        result = await record_market_sentiment_snapshot(session)

    assert result["skipped"] is False
    assert result["snapshot"]["score"] == 72.5
    mock_insert.assert_awaited_once()


@pytest.mark.asyncio
async def test_load_market_sentiment_overview_disabled():
    session = AsyncMock()
    with patch("features.sentiment.market_sentiment.get_settings") as mock_settings:
        mock_settings.return_value.sentiment_enabled = False
        mock_settings.return_value.market_sentiment_window_hours = 24
        payload = await load_market_sentiment_overview(session)
    assert payload["available"] is False
    assert payload["current_score"] == 50.0
    assert payload["points"] == []


@pytest.mark.asyncio
async def test_load_market_sentiment_overview_returns_points():
    session = AsyncMock()
    recorded_at = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    points = [{
        "id": 1,
        "recorded_at": recorded_at,
        "window_hours": 24,
        "score": 72.5,
        "article_count": 3,
        "bullish_count": 2,
        "bearish_count": 0,
        "neutral_count": 1,
    }]

    with patch("features.sentiment.market_sentiment.get_settings") as mock_settings, patch(
        "features.sentiment.market_sentiment.market_sentiment_dal.list_snapshots",
        new=AsyncMock(return_value=points),
    ):
        mock_settings.return_value.sentiment_enabled = True
        mock_settings.return_value.market_sentiment_window_hours = 24
        payload = await load_market_sentiment_overview(session, hours=168)

    assert payload["available"] is True
    assert payload["current_score"] == 72.5
    assert payload["current_article_count"] == 3
    assert len(payload["points"]) == 1
