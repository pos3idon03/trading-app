from dataclasses import dataclass
from datetime import date

from features.sentiment.text_preprocessor import build_article_text


def signed_score(positive: float, negative: float) -> float:
    return float(positive - negative)


@dataclass(frozen=True)
class RollupKey:
    symbol: str
    day: date
    model_name: str
    model_version: str


def collect_rollup_keys(
    articles: list[dict],
    *,
    model_name: str,
    model_version: str,
) -> set[RollupKey]:
    keys: set[RollupKey] = set()
    for article in articles:
        day = article["published_at"].date()
        for ticker in article.get("tickers") or []:
            symbol = str(ticker).upper().strip()
            if symbol:
                keys.add(RollupKey(symbol, day, model_name, model_version))
    return keys


def build_daily_rollup(
    symbol: str,
    day: date,
    articles: list[dict],
    *,
    model_name: str,
    model_version: str,
) -> dict:
    matching = [
        article
        for article in articles
        if day == article["published_at"].date()
        and symbol in {str(t).upper() for t in (article.get("tickers") or [])}
    ]
    if not matching:
        return {
            "symbol": symbol,
            "date": day,
            "model_name": model_name,
            "model_version": model_version,
            "article_count": 0,
            "avg_score": 0.0,
            "bullish_pct": 0.0,
            "bearish_pct": 0.0,
        }

    scores = [
        signed_score(article["score_positive"], article["score_negative"])
        for article in matching
    ]
    bullish = sum(1 for article in matching if article["label"] == "positive")
    bearish = sum(1 for article in matching if article["label"] == "negative")
    count = len(matching)
    return {
        "symbol": symbol,
        "date": day,
        "model_name": model_name,
        "model_version": model_version,
        "article_count": count,
        "avg_score": sum(scores) / count,
        "bullish_pct": bullish / count,
        "bearish_pct": bearish / count,
    }


def rollup_input_from_article(article: dict, score: dict) -> dict:
    return {
        "id": article["id"],
        "published_at": article["published_at"],
        "tickers": article.get("tickers") or [],
        "label": score["label"],
        "score_positive": score["score_positive"],
        "score_negative": score["score_negative"],
        "score_neutral": score["score_neutral"],
    }


def prepare_scoring_text(article: dict, max_chars: int) -> tuple[str, str]:
    from features.sentiment.text_preprocessor import hash_text, normalize_text

    text = build_article_text(article.get("title", ""), article.get("description"))
    normalized = normalize_text(text, max_chars)
    return normalized, hash_text(normalized)
