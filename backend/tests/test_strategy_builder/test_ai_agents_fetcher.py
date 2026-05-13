"""Tests for AI agents fetcher used by the Strategy Builder."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.strategy_builder.ai_agents_fetcher import (
    _build_summary,
    _resolve_macro_score,
    get_latest_agent_analysis,
)


def _make_record(
    *,
    macro_score: float | None = None,
    signal: dict | None = None,
):
    record = MagicMock()
    record.id = 1
    record.bias = "bullish"
    record.conviction_score = 0.82
    record.sentiment_score = 0.6
    record.macro_score = macro_score
    record.signal = signal or {}
    record.created_at = datetime(2024, 5, 9, tzinfo=timezone.utc)
    return record


class TestResolveMacroScore:
    def test_prefers_column_value_over_blob(self):
        record = _make_record(macro_score=0.55, signal={"macro_score": 0.99})
        assert _resolve_macro_score(record, record.signal) == pytest.approx(0.55)

    def test_returns_column_zero_without_falsy_bug(self):
        record = _make_record(macro_score=0.0, signal={"macro_score": 0.99})
        assert _resolve_macro_score(record, record.signal) == pytest.approx(0.0)

    def test_falls_back_to_blob_macro_score_when_column_is_none(self):
        record = _make_record(macro_score=None, signal={"macro_score": 0.45})
        assert _resolve_macro_score(record, record.signal) == pytest.approx(0.45)

    def test_falls_back_to_blob_macro_sentiment_score_key(self):
        record = _make_record(macro_score=None, signal={"macro_sentiment_score": -0.3})
        assert _resolve_macro_score(record, record.signal) == pytest.approx(-0.3)

    def test_returns_none_when_both_sources_missing(self):
        record = _make_record(macro_score=None, signal={})
        assert _resolve_macro_score(record, record.signal) is None

    def test_blob_zero_is_returned_correctly(self):
        record = _make_record(macro_score=None, signal={"macro_score": 0.0})
        assert _resolve_macro_score(record, record.signal) == pytest.approx(0.0)

    def test_negative_macro_score_from_column(self):
        record = _make_record(macro_score=-0.75)
        assert _resolve_macro_score(record, {}) == pytest.approx(-0.75)


class TestBuildSummary:
    def test_builds_summary_with_macro_score_from_column(self):
        record = _make_record(
            macro_score=0.55,
            signal={
                "fundamental_summary": "Solid.",
                "macro_summary": "Supportive rates.",
                "reasoning": "Strong thesis.",
                "key_risk": "Supply chain.",
            },
        )
        summary = _build_summary(record)
        assert summary.analysis_id == 1
        assert summary.bias == "bullish"
        assert summary.conviction_score == pytest.approx(0.82)
        assert summary.macro_score == pytest.approx(0.55)
        assert summary.sentiment_score == pytest.approx(0.6)
        assert summary.fundamental_summary == "Solid."

    def test_builds_summary_with_macro_score_from_blob_fallback(self):
        record = _make_record(
            macro_score=None,
            signal={"macro_score": 0.33},
        )
        summary = _build_summary(record)
        assert summary.macro_score == pytest.approx(0.33)

    def test_macro_score_none_when_missing_everywhere(self):
        record = _make_record(macro_score=None, signal={})
        summary = _build_summary(record)
        assert summary.macro_score is None

    def test_zero_macro_score_not_treated_as_falsy(self):
        record = _make_record(macro_score=0.0)
        summary = _build_summary(record)
        assert summary.macro_score == pytest.approx(0.0)


class TestGetLatestAgentAnalysis:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_records(self):
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await get_latest_agent_analysis(session, asset_id=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_summary_for_latest_record(self):
        record = _make_record(
            macro_score=0.45,
            signal={"fundamental_summary": "Strong.", "macro_summary": "OK."},
        )
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = record
        session.execute = AsyncMock(return_value=mock_result)

        summary = await get_latest_agent_analysis(session, asset_id=1)
        assert summary is not None
        assert summary.macro_score == pytest.approx(0.45)
