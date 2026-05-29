from dataclasses import dataclass


@dataclass(frozen=True)
class EffectiveSentiment:
    label: str
    score_positive: float
    score_negative: float
    score_neutral: float
    confidence: float
    source: str


def _normalize_label(label: str) -> str:
    normalized = label.lower().strip()
    if normalized in ("positive", "negative", "neutral"):
        return normalized
    return "neutral"


def label_to_scores(label: str, confidence: float) -> tuple[float, float, float]:
    label = _normalize_label(label)
    confidence = max(0.0, min(1.0, float(confidence)))
    remainder = max(0.0, 1.0 - confidence)
    split = remainder / 2.0
    if label == "positive":
        return confidence, split, split
    if label == "negative":
        return split, confidence, split
    return split, split, confidence


def resolve_effective_sentiment(
    finbert: dict | None,
    enrichment: dict | None,
) -> EffectiveSentiment | None:
    if finbert is None:
        return None

    finbert_label = _normalize_label(finbert["label"])
    if enrichment and enrichment.get("refined_label") and finbert_label == "neutral":
        label = _normalize_label(enrichment["refined_label"])
        confidence = float(enrichment.get("refined_confidence") or 0.0)
        return EffectiveSentiment(
            label=label,
            score_positive=float(enrichment["score_positive"]),
            score_negative=float(enrichment["score_negative"]),
            score_neutral=float(enrichment["score_neutral"]),
            confidence=confidence,
            source="gemini",
        )

    return EffectiveSentiment(
        label=finbert_label,
        score_positive=float(finbert["score_positive"]),
        score_negative=float(finbert["score_negative"]),
        score_neutral=float(finbert["score_neutral"]),
        confidence=float(finbert["confidence"]),
        source="finbert",
    )


def effective_to_dict(effective: EffectiveSentiment | None) -> dict | None:
    if effective is None:
        return None
    return {
        "label": effective.label,
        "score_positive": effective.score_positive,
        "score_negative": effective.score_negative,
        "score_neutral": effective.score_neutral,
        "confidence": effective.confidence,
        "source": effective.source,
    }
