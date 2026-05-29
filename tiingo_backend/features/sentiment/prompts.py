import json
from typing import Any


def build_sentiment_prompt(article: dict) -> str:
    tickers = ", ".join(article.get("tickers") or []) or "unknown"
    title = article.get("title") or ""
    description = article.get("description") or ""
    finbert_label = article.get("finbert_label") or "neutral"
    return (
        "You are a financial news sentiment analyst. "
        "Use Google Search to gather recent context about this headline, then classify "
        "market sentiment for the mentioned tickers.\n\n"
        f"Title: {title}\n"
        f"Summary: {description}\n"
        f"Tickers: {tickers}\n"
        f"Initial FinBERT label: {finbert_label}\n\n"
        "Return ONLY valid JSON with this schema:\n"
        "{\n"
        '  "label": "positive|negative|neutral",\n'
        '  "confidence": 0.0,\n'
        '  "rationale": "short explanation",\n'
        '  "ticker_impacts": [{"symbol": "AAPL", "impact": "positive|negative|neutral", "reason": "..."}]\n'
        "}\n"
        "Focus on investable sentiment for the tickers. Be conservative when evidence is mixed."
    )


def parse_analysis_json(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    payload = json.loads(text)
    label = str(payload.get("label") or "neutral").lower()
    if label not in ("positive", "negative", "neutral"):
        label = "neutral"
    confidence = float(payload.get("confidence") or 0.5)
    return {
        "label": label,
        "confidence": max(0.0, min(1.0, confidence)),
        "rationale": str(payload.get("rationale") or ""),
        "ticker_impacts": payload.get("ticker_impacts") or [],
    }
