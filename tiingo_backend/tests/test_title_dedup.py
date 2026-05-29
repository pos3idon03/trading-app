from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from features.sentiment.daily_aggregator import build_daily_rollup


def test_build_daily_rollup_uses_refined_label():
    day = datetime(2024, 6, 1, tzinfo=timezone.utc).date()
    rollup = build_daily_rollup(
        "GOOG",
        day,
        [
            {
                "published_at": datetime(2024, 6, 1, tzinfo=timezone.utc),
                "tickers": ["GOOG"],
                "label": "positive",
                "score_positive": 0.8,
                "score_negative": 0.1,
                "score_neutral": 0.1,
            }
        ],
        model_name="ProsusAI/finbert",
        model_version="1",
    )
    assert rollup["bullish_pct"] == 1.0
    assert rollup["avg_score"] == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_bulk_insert_skips_duplicate_title_within_window():
    from dal import news_dal

    published = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalar_one_or_none=lambda: 99)

    articles = [
        {
            "published_at": published,
            "title": "Same Headline",
            "url": "https://example.com/a",
            "description": "a",
            "source": "tiingo",
            "tickers": ["AAPL"],
            "tags": [],
        }
    ]
    inserted = await news_dal.bulk_insert_news(session, articles)
    assert inserted == 0
    session.execute.assert_called()
