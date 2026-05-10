"""Tests verifying that the agent analysis route validates asset existence."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from dtos.ai_agent_dto import AgentAnalysisRequest


# ---------------------------------------------------------------------------
# POST /analyze: rejects unknown tickers with 404
# ---------------------------------------------------------------------------

class TestAnalyzeRouteAssetValidation:
    @pytest.mark.asyncio
    async def test_unknown_asset_raises_404(self):
        from routes.ai_agents import analyze_asset

        req = AgentAnalysisRequest(symbol="FAKE")
        session = AsyncMock()

        with patch("routes.ai_agents.get_asset_id_by_symbol", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc_info:
                await analyze_asset(req, session)

        assert exc_info.value.status_code == 404
        assert "not registered" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_known_asset_proceeds_to_create_analysis(self):
        from routes.ai_agents import analyze_asset
        from features.ai_agents.crew import TradingSignal

        req = AgentAnalysisRequest(symbol="aapl")
        session = AsyncMock()

        mock_signal = TradingSignal(
            asset="AAPL",
            bias="bullish",
            conviction_score=0.8,
            fundamental_summary="Strong.",
            macro_summary="Supportive.",
            sentiment_score=0.6,
            reasoning="Thesis.",
            key_risk="Regulatory.",
            timestamp="2024-05-09T12:00:00Z",
            raw_output="",
            fundamental_report="Fund.",
            macro_report="Macro.",
            sentiment_report="Sent.",
            duration_ms=1000,
        )

        with (
            patch("routes.ai_agents.get_asset_id_by_symbol", new=AsyncMock(return_value=1)),
            patch("routes.ai_agents.create_analysis", new=AsyncMock(return_value=99)),
            patch("routes.ai_agents.run_analysis_crew", return_value=mock_signal),
            patch("routes.ai_agents.update_analysis_result", new=AsyncMock()),
        ):
            response = await analyze_asset(req, session)

        assert response.analysis_id == 99
        assert response.asset_id == 1
        assert response.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_symbol_is_uppercased_before_lookup(self):
        from routes.ai_agents import analyze_asset

        req = AgentAnalysisRequest(symbol="tsla")
        session = AsyncMock()
        looked_up = {}

        async def capture_lookup(session, symbol):
            looked_up["symbol"] = symbol
            return None

        with patch("routes.ai_agents.get_asset_id_by_symbol", side_effect=capture_lookup):
            with pytest.raises(HTTPException):
                await analyze_asset(req, session)

        assert looked_up["symbol"] == "TSLA"


# ---------------------------------------------------------------------------
# GET /{analysis_id}: asset_id is included in response
# ---------------------------------------------------------------------------

class TestGetAgentAnalysisAssetId:
    @pytest.mark.asyncio
    async def test_asset_id_included_in_response(self):
        from routes.ai_agents import get_agent_analysis
        from unittest.mock import MagicMock

        session = AsyncMock()
        mock_record = MagicMock()
        mock_record.id = 10
        mock_record.asset_id = 3
        mock_record.symbol = "AAPL"
        mock_record.status = "done"
        mock_record.signal = {
            "asset": "AAPL",
            "bias": "bullish",
            "conviction_score": 0.8,
            "fundamental_summary": "Strong.",
            "macro_summary": "Good.",
            "sentiment_score": 0.5,
            "reasoning": "Thesis.",
            "key_risk": "Risk.",
            "timestamp": "2024-05-09T00:00:00Z",
        }
        mock_record.fundamental_report = "Fund."
        mock_record.macro_report = "Macro."
        mock_record.sentiment_report = "Sent."
        mock_record.duration_ms = 2000
        mock_record.error_message = None
        mock_record.provider_used = None

        with patch("routes.ai_agents.get_analysis", new=AsyncMock(return_value=mock_record)):
            response = await get_agent_analysis(10, session)

        assert response.asset_id == 3
