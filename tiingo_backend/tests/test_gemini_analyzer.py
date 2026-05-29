import json
from unittest.mock import MagicMock, patch

import pytest

from features.sentiment.gemini_analyzer import _extract_grounding_metadata, analyze_article
from features.sentiment.prompts import parse_analysis_json


def test_parse_analysis_json():
    payload = parse_analysis_json(
        '{"label":"positive","confidence":0.72,"rationale":"Strong demand","ticker_impacts":[]}'
    )
    assert payload["label"] == "positive"
    assert payload["confidence"] == pytest.approx(0.72)


def test_parse_analysis_json_from_markdown_fence():
    payload = parse_analysis_json(
        '```json\n{"label":"negative","confidence":0.6,"rationale":"Weak outlook","ticker_impacts":[]}\n```'
    )
    assert payload["label"] == "negative"


def test_analyze_sync_uses_search_without_json_mime():
    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "label": "positive",
            "confidence": 0.7,
            "rationale": "Strong earnings",
            "ticker_impacts": [],
        }
    )
    mock_response.candidates = []

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_types = MagicMock()
    mock_types.GenerateContentConfig = lambda **kwargs: kwargs
    mock_types.Tool = lambda **kwargs: kwargs
    mock_types.GoogleSearch = lambda: object()

    with patch("features.sentiment.gemini_analyzer.get_settings") as mock_settings, patch.dict(
        "sys.modules",
        {"google.genai": MagicMock(types=mock_types), "google": MagicMock(genai=mock_genai)},
    ):
        mock_settings.return_value.gemini_api_key = "test-key"
        mock_settings.return_value.sentiment_llm_model = "gemini-2.5-flash"

        from features.sentiment.gemini_analyzer import _analyze_sync

        result = _analyze_sync(
            {"title": "Test", "description": "Summary", "tickers": ["AAPL"], "finbert_label": "neutral"}
        )

    config = mock_client.models.generate_content.call_args.kwargs["config"]
    assert "response_mime_type" not in config
    assert result.refined_label == "positive"


def test_extract_grounding_metadata_empty():
    assert _extract_grounding_metadata(MagicMock(candidates=None)) == ([], [])


@pytest.mark.asyncio
async def test_analyze_article_mocked():
    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "label": "negative",
            "confidence": 0.81,
            "rationale": "Competitive pressure",
            "ticker_impacts": [],
        }
    )
    mock_response.candidates = []

    with patch("features.sentiment.gemini_analyzer.get_settings") as mock_settings, patch(
        "features.sentiment.gemini_analyzer._analyze_sync",
        return_value=MagicMock(
            refined_label="negative",
            refined_confidence=0.81,
            score_positive=0.095,
            score_negative=0.81,
            score_neutral=0.095,
            rationale="Competitive pressure",
            citations=[],
            search_queries=["grok ai model"],
            raw_response={},
        ),
    ):
        mock_settings.return_value.gemini_api_key = "test-key"
        mock_settings.return_value.sentiment_llm_timeout_seconds = 30
        result = await analyze_article({"title": "Test", "description": "Summary", "tickers": ["GOOG"]})

    assert result.refined_label == "negative"
    assert result.refined_confidence == pytest.approx(0.81)
