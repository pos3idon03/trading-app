from config import get_settings
from features.sentiment.finbert_scorer import clear_model_cache, score_texts

__all__ = ["clear_model_cache", "get_scorer", "score_texts"]


def get_scorer():
    settings = get_settings()
    if not settings.sentiment_enabled:
        raise RuntimeError("Sentiment analysis is disabled (SENTIMENT_ENABLED=false)")
    return score_texts
