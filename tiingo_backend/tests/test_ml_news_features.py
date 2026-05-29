from datetime import date, datetime, timezone

from features.ml.news_features import build_news_feature_matrix


def test_build_news_feature_matrix_aligns_to_bars():
    bars = [
        {"time": datetime(2024, 6, 1, tzinfo=timezone.utc)},
        {"time": datetime(2024, 6, 2, tzinfo=timezone.utc)},
    ]
    daily_rows = [
        {
            "date": date(2024, 6, 1),
            "avg_score": 0.4,
            "article_count": 2,
            "bullish_pct": 1.0,
            "bearish_pct": 0.0,
        }
    ]
    names, rows, warnings = build_news_feature_matrix(bars, daily_rows)
    assert names
    assert rows[0] is not None
    assert rows[0][0] == 0.4
    assert rows[0][1] == 2.0
    assert rows[1] is not None
    assert not warnings


def test_build_news_feature_matrix_empty_daily():
    bars = [{"time": datetime(2024, 6, 1, tzinfo=timezone.utc)}]
    names, rows, warnings = build_news_feature_matrix(bars, [])
    assert names == []
    assert rows == []
    assert warnings
