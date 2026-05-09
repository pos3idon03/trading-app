"""Tests for crew orchestration and signal parsing.

LLM calls are mocked entirely — we test the wiring, parsing, and fallback logic.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from features.ai_agents.crew import (
    TradingSignal,
    _default_signal,
    _parse_signal,
    _signal_from_dict,
)


# ---------------------------------------------------------------------------
# _parse_signal
# ---------------------------------------------------------------------------


class TestParseSignal:
    def _valid_json_output(self) -> str:
        signal = {
            "asset": "AAPL",
            "bias": "bullish",
            "conviction_score": 0.82,
            "fundamental_summary": "Strong revenue growth with improving margins.",
            "macro_summary": "Fed pausing; supportive rate environment.",
            "sentiment_score": 0.6,
            "reasoning": "Multiple catalysts align for a bullish thesis on AAPL.",
            "key_risk": "Regulatory scrutiny in EU may pressure margins.",
            "timestamp": "2024-05-09T12:00:00Z",
        }
        return f"Analysis complete.\n{json.dumps(signal)}\n"

    def test_parses_valid_json_from_output(self):
        signal = _parse_signal(self._valid_json_output(), "AAPL")
        assert signal.asset == "AAPL"
        assert signal.bias == "bullish"
        assert signal.conviction_score == pytest.approx(0.82)
        assert signal.sentiment_score == pytest.approx(0.6)

    def test_falls_back_to_default_on_malformed_output(self):
        signal = _parse_signal("No JSON here at all.", "AAPL")
        assert signal.asset == "AAPL"
        assert signal.bias == "neutral"
        assert signal.conviction_score == 0.0

    def test_parses_signal_embedded_in_prose(self):
        output = (
            "After careful analysis here is my recommendation:\n"
            '{"asset": "MSFT", "bias": "bearish", "conviction_score": 0.7, '
            '"fundamental_summary": "Slowing cloud", "macro_summary": "Rate pressure", '
            '"sentiment_score": -0.4, "reasoning": "Bears have edge.", "key_risk": "AI competition.", '
            '"timestamp": "2024-05-09T00:00:00Z"}'
        )
        signal = _parse_signal(output, "MSFT")
        assert signal.bias == "bearish"
        assert signal.asset == "MSFT"


# ---------------------------------------------------------------------------
# _signal_from_dict
# ---------------------------------------------------------------------------


class TestSignalFromDict:
    def _base_dict(self) -> dict:
        return {
            "asset": "NVDA",
            "bias": "bullish",
            "conviction_score": 0.9,
            "fundamental_summary": "AI tailwind.",
            "macro_summary": "Supportive rates.",
            "sentiment_score": 0.75,
            "reasoning": "Strong AI demand drives upside.",
            "key_risk": "Supply chain concentration.",
            "timestamp": "2024-05-09T00:00:00Z",
        }

    def test_creates_signal_with_all_fields(self):
        signal = _signal_from_dict(self._base_dict(), "NVDA")
        assert isinstance(signal, TradingSignal)
        assert signal.conviction_score == pytest.approx(0.9)
        assert signal.reasoning == "Strong AI demand drives upside."

    def test_handles_missing_optional_fields_with_defaults(self):
        data = {"bias": "neutral"}
        signal = _signal_from_dict(data, "TEST")
        assert signal.asset == "TEST"
        assert signal.bias == "neutral"
        assert signal.conviction_score == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# _default_signal
# ---------------------------------------------------------------------------


class TestDefaultSignal:
    def test_returns_neutral_signal(self):
        signal = _default_signal("AAPL", "raw output text")
        assert signal.bias == "neutral"
        assert signal.conviction_score == 0.0
        assert signal.asset == "AAPL"

    def test_includes_raw_output_in_reasoning(self):
        signal = _default_signal("AAPL", "some raw text output")
        assert "some raw text output" in signal.reasoning


# ---------------------------------------------------------------------------
# run_analysis_crew (integration-level mock of CrewAI)
# ---------------------------------------------------------------------------


class TestRunAnalysisCrew:
    def _mock_crew_result(self) -> str:
        return json.dumps({
            "asset": "AAPL",
            "bias": "bullish",
            "conviction_score": 0.78,
            "fundamental_summary": "Solid balance sheet.",
            "macro_summary": "Supportive macro.",
            "sentiment_score": 0.5,
            "reasoning": "Multiple positive signals.",
            "key_risk": "Valuation stretch.",
            "timestamp": "2024-05-09T00:00:00Z",
        })

    def _crew_patches(self, mock_crew, mock_task):
        return (
            patch("features.ai_agents.crew.Crew", return_value=mock_crew),
            patch("features.ai_agents.crew.get_llm_for_crew", return_value="openai/gpt-4o-mini"),
            patch("features.ai_agents.crew.build_fundamental_task", return_value=mock_task),
            patch("features.ai_agents.crew.build_macro_task", return_value=mock_task),
            patch("features.ai_agents.crew.build_sentiment_task", return_value=mock_task),
            patch("features.ai_agents.crew.build_synthesis_task", return_value=mock_task),
            patch("features.ai_agents.crew.build_fundamental_agent", return_value=MagicMock()),
            patch("features.ai_agents.crew.build_macro_agent", return_value=MagicMock()),
            patch("features.ai_agents.crew.build_sentiment_agent", return_value=MagicMock()),
            patch("features.ai_agents.crew.build_manager_agent", return_value=MagicMock()),
        )

    def test_crew_run_returns_trading_signal(self):
        from features.ai_agents.crew import run_analysis_crew

        mock_crew = MagicMock()
        mock_crew.kickoff.return_value = self._mock_crew_result()

        mock_task = MagicMock()
        mock_task.output = MagicMock()
        mock_task.output.raw = "Agent task output"

        with self._crew_patches(mock_crew, mock_task):
            result = run_analysis_crew("AAPL")

        assert isinstance(result, TradingSignal)
        assert result.asset == "AAPL"
        assert result.bias == "bullish"
        assert result.duration_ms >= 0
        assert result.fundamental_report == "Agent task output"

    def test_crew_run_falls_back_on_parse_failure(self):
        from features.ai_agents.crew import run_analysis_crew

        mock_crew = MagicMock()
        mock_crew.kickoff.return_value = "This is not valid JSON output at all."

        mock_task = MagicMock()
        mock_task.output = None

        with self._crew_patches(mock_crew, mock_task):
            result = run_analysis_crew("AAPL")

        assert result.bias == "neutral"
        assert result.conviction_score == 0.0

    def test_crew_run_sets_provider_used(self):
        from features.ai_agents.crew import run_analysis_crew

        mock_crew = MagicMock()
        mock_crew.kickoff.return_value = self._mock_crew_result()

        mock_task = MagicMock()
        mock_task.output = MagicMock()
        mock_task.output.raw = "output"

        with self._crew_patches(mock_crew, mock_task):
            result = run_analysis_crew("AAPL", llm="gpt-4o-mini")

        assert result.provider_used == "openai/gpt-4o-mini"
