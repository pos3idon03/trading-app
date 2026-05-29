from dataclasses import dataclass

from config import get_settings

_PIPELINE = None
_TOKENIZER = None
_MODEL = None


@dataclass
class SentimentScore:
    label: str
    score_positive: float
    score_negative: float
    score_neutral: float
    confidence: float


def _load_pipeline():
    global _PIPELINE, _TOKENIZER, _MODEL
    if _PIPELINE is not None:
        return _PIPELINE

    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
    except ImportError as exc:
        raise RuntimeError(
            "Sentiment analysis requires transformers and torch. "
            "Install with: pip install -r requirements-sentiment.txt"
        ) from exc

    settings = get_settings()
    model_name = settings.sentiment_model_name
    _TOKENIZER = AutoTokenizer.from_pretrained(model_name)
    _MODEL = AutoModelForSequenceClassification.from_pretrained(model_name)
    _PIPELINE = pipeline(
        "text-classification",
        model=_MODEL,
        tokenizer=_TOKENIZER,
        device=-1 if settings.sentiment_device == "cpu" else 0,
        top_k=None,
    )
    return _PIPELINE


def clear_model_cache() -> None:
    global _PIPELINE, _TOKENIZER, _MODEL
    _PIPELINE = None
    _TOKENIZER = None
    _MODEL = None


def _label_from_scores(scores: list[dict]) -> SentimentScore:
    by_label = {item["label"].lower(): float(item["score"]) for item in scores}
    positive = by_label.get("positive", 0.0)
    negative = by_label.get("negative", 0.0)
    neutral = by_label.get("neutral", 0.0)
    label_scores = {
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
    }
    label = max(label_scores, key=label_scores.get)
    confidence = label_scores[label]
    return SentimentScore(
        label=label,
        score_positive=positive,
        score_negative=negative,
        score_neutral=neutral,
        confidence=confidence,
    )


def score_texts(texts: list[str]) -> list[SentimentScore]:
    if not texts:
        return []
    pipe = _load_pipeline()
    raw = pipe(texts, truncation=True)
    if texts and isinstance(raw[0], dict):
        raw = [raw]
    return [_label_from_scores(item) for item in raw]
