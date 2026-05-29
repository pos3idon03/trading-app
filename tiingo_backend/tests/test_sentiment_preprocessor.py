from datetime import date, datetime, timezone

import pytest

from features.sentiment.daily_aggregator import (
    build_daily_rollup,
    collect_rollup_keys,
    signed_score,
)
from features.sentiment.text_preprocessor import build_article_text, hash_text, normalize_text, title_fingerprint


def test_build_article_text_combines_title_and_description():
    text = build_article_text("Apple beats earnings", "Shares rose 3%.")
    assert text == "Apple beats earnings. Shares rose 3%."


def test_normalize_text_truncates():
    text = normalize_text("a " * 300, 20)
    assert len(text) <= 20


def test_title_fingerprint_is_stable():
    assert title_fingerprint("Hello World") == title_fingerprint("  hello   world ")
    assert title_fingerprint("Hello") != title_fingerprint("World")


def test_hash_text_is_stable():
    assert hash_text("hello") == hash_text("hello")
    assert hash_text("hello") != hash_text("world")


def test_signed_score():
    assert signed_score(0.8, 0.1) == pytest.approx(0.7)


def test_build_daily_rollup():
    day = date(2024, 6, 1)
    ts = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    rollup = build_daily_rollup(
        "AAPL",
        day,
        [
            {
                "published_at": ts,
                "tickers": ["AAPL"],
                "label": "positive",
                "score_positive": 0.8,
                "score_negative": 0.1,
                "score_neutral": 0.1,
            },
            {
                "published_at": ts,
                "tickers": ["AAPL"],
                "label": "negative",
                "score_positive": 0.1,
                "score_negative": 0.7,
                "score_neutral": 0.2,
            },
        ],
        model_name="ProsusAI/finbert",
        model_version="1",
    )
    assert rollup["article_count"] == 2
    assert rollup["bullish_pct"] == 0.5
    assert rollup["bearish_pct"] == 0.5


def test_collect_rollup_keys():
    ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
    keys = collect_rollup_keys(
        [{"published_at": ts, "tickers": ["AAPL", "MSFT"]}],
        model_name="ProsusAI/finbert",
        model_version="1",
    )
    assert len(keys) == 2
