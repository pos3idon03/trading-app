from datetime import date, datetime, timedelta, timezone
from typing import Optional

from features.ml.asof_join import bar_dates_from_bars

NEWS_FEATURE_NAMES = [
    "news_sent_avg_score_24h",
    "news_sent_article_count_24h",
    "news_sent_avg_score_7d",
    "news_sent_momentum_7d",
]


def _daily_index(daily_rows: list[dict]) -> dict[date, dict]:
    return {row["date"]: row for row in daily_rows}


def _rolling_avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _bar_end_datetime(bar: dict) -> datetime:
    bar_time = bar["time"]
    if isinstance(bar_time, datetime):
        return bar_time if bar_time.tzinfo else bar_time.replace(tzinfo=timezone.utc)
    if isinstance(bar_time, date):
        return datetime(bar_time.year, bar_time.month, bar_time.day, tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(bar_time).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _window_dates(window_start: datetime, window_end: datetime) -> list[date]:
    current = window_start.date()
    end = window_end.date()
    dates: list[date] = []
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def _aggregate_window(
    window_start: datetime,
    window_end: datetime,
    by_date: dict[date, dict],
) -> tuple[float | None, float]:
    scores: list[float] = []
    article_count = 0.0
    for day in _window_dates(window_start, window_end):
        row = by_date.get(day)
        if not row or row["article_count"] <= 0:
            continue
        scores.append(float(row["avg_score"]))
        article_count += float(row["article_count"])
    avg_score = _rolling_avg(scores)
    return avg_score, article_count


def _score_for_bar(
    bar: dict,
    bar_date: date,
    by_date: dict[date, dict],
) -> tuple[float | None, float, float | None, float | None]:
    bar_end = _bar_end_datetime(bar)
    window_start = bar_end - timedelta(hours=24)
    score_24h, count_24h = _aggregate_window(window_start, bar_end, by_date)

    recent_scores: list[float] = []
    prior_scores: list[float] = []
    for offset in range(7):
        current = bar_date - timedelta(days=offset)
        row = by_date.get(current)
        if row and row["article_count"] > 0:
            recent_scores.append(float(row["avg_score"]))
    for offset in range(7, 14):
        current = bar_date - timedelta(days=offset)
        row = by_date.get(current)
        if row and row["article_count"] > 0:
            prior_scores.append(float(row["avg_score"]))

    score_7d = _rolling_avg(recent_scores)
    prior_7d = _rolling_avg(prior_scores)
    momentum = None
    if score_7d is not None and prior_7d is not None:
        momentum = score_7d - prior_7d

    return score_24h, count_24h, score_7d, momentum


def build_news_feature_matrix(
    bars: list[dict],
    daily_rows: list[dict],
) -> tuple[list[str], list[Optional[list[float]]], list[str]]:
    if not bars:
        return [], [], []

    warnings: list[str] = []
    if not daily_rows:
        warnings.append("No ingested news sentiment daily rows for this symbol; news columns omitted.")
        return [], [], warnings

    by_date = _daily_index(daily_rows)
    bar_dates = bar_dates_from_bars(bars)
    rows: list[Optional[list[float]]] = []

    for bar, bar_date in zip(bars, bar_dates):
        score_24h, count_24h, score_7d, momentum = _score_for_bar(bar, bar_date, by_date)
        if score_24h is None and score_7d is None:
            rows.append(None)
            continue
        rows.append(
            [
                score_24h if score_24h is not None else 0.0,
                count_24h,
                score_7d if score_7d is not None else 0.0,
                momentum if momentum is not None else 0.0,
            ]
        )

    if all(row is None for row in rows):
        warnings.append("News sentiment rows exist but none align with bar dates.")
        return [], [], warnings

    return list(NEWS_FEATURE_NAMES), rows, warnings
