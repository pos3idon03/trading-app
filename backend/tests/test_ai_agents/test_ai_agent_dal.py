"""Tests for AI agent DAL — update_analysis_result persists macro_score."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dal.ai_agent_dal import update_analysis_result


def _make_signal_dict(macro_score: float = 0.45) -> dict:
    return {
        "asset": "AAPL",
        "bias": "bullish",
        "conviction_score": 0.82,
        "fundamental_summary": "Strong.",
        "macro_summary": "Supportive.",
        "macro_score": macro_score,
        "sentiment_score": 0.6,
        "reasoning": "Bullish thesis.",
        "key_risk": "Regulatory.",
        "timestamp": "2024-05-09T12:00:00Z",
        "provider_used": "",
    }


class TestUpdateAnalysisResult:
    @pytest.mark.asyncio
    async def test_persists_macro_score(self):
        session = AsyncMock()
        record = MagicMock()
        session.get = AsyncMock(return_value=record)

        await update_analysis_result(
            session,
            analysis_id=1,
            signal=_make_signal_dict(0.55),
            fundamental_report="fund report",
            macro_report="macro report",
            sentiment_report="sentiment report",
            bias="bullish",
            conviction_score=0.82,
            macro_score=0.55,
            sentiment_score=0.6,
            duration_ms=45000,
            provider_used="openai/gpt-4o-mini",
        )

        assert record.macro_score == pytest.approx(0.55)

    @pytest.mark.asyncio
    async def test_persists_negative_macro_score(self):
        session = AsyncMock()
        record = MagicMock()
        session.get = AsyncMock(return_value=record)

        await update_analysis_result(
            session,
            analysis_id=2,
            signal=_make_signal_dict(-0.7),
            fundamental_report="",
            macro_report="",
            sentiment_report="",
            bias="bearish",
            conviction_score=0.7,
            macro_score=-0.7,
            sentiment_score=-0.5,
            duration_ms=30000,
        )

        assert record.macro_score == pytest.approx(-0.7)

    @pytest.mark.asyncio
    async def test_persists_zero_macro_score(self):
        session = AsyncMock()
        record = MagicMock()
        session.get = AsyncMock(return_value=record)

        await update_analysis_result(
            session,
            analysis_id=3,
            signal=_make_signal_dict(0.0),
            fundamental_report="",
            macro_report="",
            sentiment_report="",
            bias="neutral",
            conviction_score=0.5,
            macro_score=0.0,
            sentiment_score=0.0,
            duration_ms=10000,
        )

        assert record.macro_score == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_raises_when_record_not_found(self):
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await update_analysis_result(
                session,
                analysis_id=999,
                signal={},
                fundamental_report="",
                macro_report="",
                sentiment_report="",
                bias="neutral",
                conviction_score=0.5,
                macro_score=0.0,
                sentiment_score=0.0,
                duration_ms=0,
            )
