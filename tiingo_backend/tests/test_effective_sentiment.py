import pytest

from features.sentiment.effective_sentiment import (
    label_to_scores,
    resolve_effective_sentiment,
)


def test_label_to_scores_positive():
    pos, neg, neu = label_to_scores("positive", 0.8)
    assert pos == pytest.approx(0.8)
    assert neg == pytest.approx(0.1)
    assert neu == pytest.approx(0.1)


def test_resolve_effective_uses_finbert_when_not_neutral():
    finbert = {
        "label": "positive",
        "score_positive": 0.9,
        "score_negative": 0.05,
        "score_neutral": 0.05,
        "confidence": 0.9,
    }
    effective = resolve_effective_sentiment(finbert, {"refined_label": "negative"})
    assert effective is not None
    assert effective.label == "positive"
    assert effective.source == "finbert"


def test_resolve_effective_overrides_neutral_with_enrichment():
    finbert = {
        "label": "neutral",
        "score_positive": 0.2,
        "score_negative": 0.2,
        "score_neutral": 0.6,
        "confidence": 0.6,
    }
    enrichment = {
        "refined_label": "positive",
        "refined_confidence": 0.75,
        "score_positive": 0.75,
        "score_negative": 0.125,
        "score_neutral": 0.125,
    }
    effective = resolve_effective_sentiment(finbert, enrichment)
    assert effective is not None
    assert effective.label == "positive"
    assert effective.source == "gemini"
