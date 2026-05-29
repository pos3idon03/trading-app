import asyncio
from dataclasses import dataclass
from typing import Any

from config import get_settings
from features.sentiment.effective_sentiment import label_to_scores
from features.sentiment.prompts import build_sentiment_prompt, parse_analysis_json
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GeminiAnalysisResult:
    refined_label: str
    refined_confidence: float
    score_positive: float
    score_negative: float
    score_neutral: float
    rationale: str
    citations: list[dict]
    search_queries: list[str]
    raw_response: dict[str, Any]


def _extract_grounding_metadata(response: Any) -> tuple[list[dict], list[str]]:
    citations: list[dict] = []
    search_queries: list[str] = []
    metadata = getattr(response, "candidates", None)
    if not metadata:
        return citations, search_queries

    for candidate in metadata:
        grounding = getattr(candidate, "grounding_metadata", None)
        if grounding is None:
            continue
        for chunk in getattr(grounding, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            if web is None:
                continue
            citations.append(
                {
                    "title": getattr(web, "title", None),
                    "url": getattr(web, "uri", None),
                }
            )
        for query in getattr(grounding, "web_search_queries", None) or []:
            search_queries.append(str(query))
    return citations, search_queries


def _analyze_sync(article: dict) -> GeminiAnalysisResult:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "Gemini enrichment requires google-genai. "
            "Install with: pip install -r requirements-llm.txt"
        ) from exc

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = build_sentiment_prompt(article)
    response = client.models.generate_content(
        model=settings.sentiment_llm_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    response_text = response.text or ""
    if not response_text.strip():
        raise RuntimeError("Gemini returned an empty response")
    parsed = parse_analysis_json(response_text)
    pos, neg, neu = label_to_scores(parsed["label"], parsed["confidence"])
    citations, search_queries = _extract_grounding_metadata(response)
    return GeminiAnalysisResult(
        refined_label=parsed["label"],
        refined_confidence=parsed["confidence"],
        score_positive=pos,
        score_negative=neg,
        score_neutral=neu,
        rationale=parsed["rationale"],
        citations=citations,
        search_queries=search_queries,
        raw_response={"text": response.text, "parsed": parsed},
    )


async def analyze_article(article: dict) -> GeminiAnalysisResult:
    settings = get_settings()
    timeout = settings.sentiment_llm_timeout_seconds
    return await asyncio.wait_for(
        asyncio.to_thread(_analyze_sync, article),
        timeout=timeout,
    )
