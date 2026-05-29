import pytest

from features.execution.risk_checker import check_sentiment_guardrail
from features.execution.signal_to_order import OrderIntent


def test_sentiment_guardrail_blocks_bearish_buy():
    intent = OrderIntent(side="buy", qty=1, reason="test")
    result = check_sentiment_guardrail(
        intent,
        avg_score_1d=-0.7,
        article_count_1d=5,
        enabled=True,
        min_score=-0.5,
        min_articles=3,
    )
    assert not result.allowed
    assert "sentiment" in (result.reason or "").lower()


def test_sentiment_guardrail_allows_when_disabled():
    intent = OrderIntent(side="buy", qty=1, reason="test")
    result = check_sentiment_guardrail(
        intent,
        avg_score_1d=-0.9,
        article_count_1d=10,
        enabled=False,
        min_score=-0.5,
        min_articles=3,
    )
    assert result.allowed


def test_sentiment_guardrail_allows_sell():
    intent = OrderIntent(side="sell", qty=1, reason="test")
    result = check_sentiment_guardrail(
        intent,
        avg_score_1d=-0.9,
        article_count_1d=10,
        enabled=True,
        min_score=-0.5,
        min_articles=3,
    )
    assert result.allowed
