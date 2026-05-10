"""Tests for AI Agent analysis HTTP route endpoints."""
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from dtos.ai_agent_dto import AgentAnalysisRequest


# ---------------------------------------------------------------------------
# AgentAnalysisRequest DTO
# ---------------------------------------------------------------------------


class TestAgentAnalysisRequestDTO:
    def test_requires_symbol(self):
        req = AgentAnalysisRequest(symbol="AAPL")
        assert req.symbol == "AAPL"

    def test_default_llm(self):
        req = AgentAnalysisRequest(symbol="AAPL")
        assert req.llm == "gpt-4o-mini"

    def test_custom_llm(self):
        req = AgentAnalysisRequest(symbol="AAPL", llm="gpt-4o")
        assert req.llm == "gpt-4o"


# ---------------------------------------------------------------------------
# POST /analyze route
# ---------------------------------------------------------------------------


def _make_trading_signal():
    from features.ai_agents.crew import TradingSignal
    return TradingSignal(
        asset="AAPL",
        bias="bullish",
        conviction_score=0.82,
        fundamental_summary="Strong fundamentals.",
        macro_summary="Supportive macro.",
        sentiment_score=0.6,
        reasoning="Multiple signals align bullishly.",
        key_risk="Regulatory headwinds.",
        timestamp="2024-05-09T12:00:00Z",
        raw_output="",
        fundamental_report="Fundamental report text.",
        macro_report="Macro report text.",
        sentiment_report="Sentiment report text.",
        duration_ms=45000,
    )


class TestAnalyzeRoute:
    @pytest.mark.asyncio
    async def test_successful_analysis_returns_signal(self):
        from routes.ai_agents import analyze_asset

        req = AgentAnalysisRequest(symbol="AAPL")
        session = AsyncMock()
        mock_signal = _make_trading_signal()

        with (
            patch("routes.ai_agents.get_asset_id_by_symbol", new=AsyncMock(return_value=1)),
            patch("routes.ai_agents.create_analysis", new=AsyncMock(return_value=1)),
            patch("routes.ai_agents.run_analysis_crew", return_value=mock_signal),
            patch("routes.ai_agents.update_analysis_result", new=AsyncMock()),
        ):
            response = await analyze_asset(req, session)

        assert response.analysis_id == 1
        assert response.asset_id == 1
        assert response.status == "done"
        assert response.signal is not None
        assert response.signal.bias == "bullish"
        assert response.signal.conviction_score == pytest.approx(0.82)
        assert response.reports is not None
        assert response.reports.fundamental == "Fundamental report text."

    @pytest.mark.asyncio
    async def test_crew_error_raises_500(self):
        from routes.ai_agents import analyze_asset

        req = AgentAnalysisRequest(symbol="AAPL")
        session = AsyncMock()

        with (
            patch("routes.ai_agents.get_asset_id_by_symbol", new=AsyncMock(return_value=2)),
            patch("routes.ai_agents.create_analysis", new=AsyncMock(return_value=1)),
            patch("routes.ai_agents.run_analysis_crew", side_effect=RuntimeError("LLM timeout")),
            patch("routes.ai_agents.update_analysis_error", new=AsyncMock()),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await analyze_asset(req, session)

        assert exc_info.value.status_code == 500
        assert "LLM timeout" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_crew_error_persists_error_status(self):
        from routes.ai_agents import analyze_asset

        req = AgentAnalysisRequest(symbol="TSLA")
        session = AsyncMock()
        mock_update_error = AsyncMock()

        with (
            patch("routes.ai_agents.get_asset_id_by_symbol", new=AsyncMock(return_value=3)),
            patch("routes.ai_agents.create_analysis", new=AsyncMock(return_value=5)),
            patch("routes.ai_agents.run_analysis_crew", side_effect=ValueError("bad input")),
            patch("routes.ai_agents.update_analysis_error", new=mock_update_error),
        ):
            with pytest.raises(HTTPException):
                await analyze_asset(req, session)

        mock_update_error.assert_awaited_once_with(session, 5, "bad input")


# ---------------------------------------------------------------------------
# GET /{analysis_id} route
# ---------------------------------------------------------------------------


class TestGetAgentAnalysisRoute:
    def _make_mock_record(self, status: str = "done"):
        rec = MagicMock()
        rec.id = 1
        rec.asset_id = 1
        rec.symbol = "AAPL"
        rec.status = status
        rec.signal = {
            "asset": "AAPL",
            "bias": "bullish",
            "conviction_score": 0.82,
            "fundamental_summary": "Strong.",
            "macro_summary": "Supportive.",
            "sentiment_score": 0.6,
            "reasoning": "Bullish thesis.",
            "key_risk": "Regulatory.",
            "timestamp": "2024-05-09T12:00:00Z",
        }
        rec.fundamental_report = "Fundamental text."
        rec.macro_report = "Macro text."
        rec.sentiment_report = "Sentiment text."
        rec.duration_ms = 45000
        rec.error_message = None
        rec.provider_used = None
        return rec

    @pytest.mark.asyncio
    async def test_returns_stored_analysis(self):
        from routes.ai_agents import get_agent_analysis

        session = AsyncMock()
        with patch("routes.ai_agents.get_analysis", new=AsyncMock(return_value=self._make_mock_record())):
            response = await get_agent_analysis(1, session)

        assert response.analysis_id == 1
        assert response.signal is not None
        assert response.signal.bias == "bullish"
        assert response.reports is not None

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self):
        from routes.ai_agents import get_agent_analysis

        session = AsyncMock()
        with patch("routes.ai_agents.get_analysis", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc_info:
                await get_agent_analysis(999, session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_no_reports_when_status_not_done(self):
        from routes.ai_agents import get_agent_analysis

        session = AsyncMock()
        pending_rec = self._make_mock_record(status="running")
        pending_rec.signal = None
        with patch("routes.ai_agents.get_analysis", new=AsyncMock(return_value=pending_rec)):
            response = await get_agent_analysis(1, session)

        assert response.signal is None
        assert response.reports is None


# ---------------------------------------------------------------------------
# _signal_to_dict helper
# ---------------------------------------------------------------------------


class TestSignalToDict:
    def test_excludes_internal_fields(self):
        from routes.ai_agents import _signal_to_dict
        from features.ai_agents.crew import TradingSignal

        signal = TradingSignal(
            asset="AAPL",
            bias="bullish",
            conviction_score=0.8,
            fundamental_summary="Strong.",
            macro_summary="Good.",
            sentiment_score=0.5,
            reasoning="Thesis.",
            key_risk="Risk.",
            timestamp="2024-05-09T00:00:00Z",
            raw_output="internal text",
            fundamental_report="fund report",
            macro_report="macro report",
            sentiment_report="sent report",
            duration_ms=1000,
        )
        d = _signal_to_dict(signal)
        assert "raw_output" not in d
        assert "fundamental_report" not in d
        assert "duration_ms" not in d
        assert d["asset"] == "AAPL"
        assert d["bias"] == "bullish"
