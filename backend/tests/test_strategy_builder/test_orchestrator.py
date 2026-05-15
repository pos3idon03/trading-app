"""Tests for the strategy builder orchestrator."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dtos.strategy_builder_dto import (
    AIAgentSummary,
    AlgoStrategySummary,
    FinancialsSummary,
    MonteCarloSummary,
)
from features.strategy_builder.orchestrator import (
    _fetch_algo_strategies,
    _fetch_ai_agents,
    _fetch_financials,
    _fetch_monte_carlo,
    build_full_strategy_response,
)
from models.strategy_builder import TradingStrategy


def _make_strategy(id_=1, asset_id=10):
    s = MagicMock(spec=TradingStrategy)
    s.id = id_
    s.asset_id = asset_id
    s.is_active = True
    s.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    s.combination_mode = "all"
    s.algo_timeframe = "1d"
    s.auto_trading_enabled = False
    s.auto_trading_started = False
    s.mc_buy_prob_positive = None
    s.mc_sell_prob_positive = None
    s.ai_buy_conviction = None
    s.ai_sell_conviction = None
    s.ai_buy_sentiment = None
    s.ai_sell_sentiment = None
    s.ai_buy_macro = None
    s.ai_sell_macro = None
    s.max_amount_per_position = None
    s.max_pct_of_capital = None
    return s


def _make_mc_summary():
    return MonteCarloSummary(
        simulation_id=1, prob_positive_return=0.62, mean_max_drawdown=-0.15,
        p5=80.0, p25=95.0, p50=105.0, p75=115.0, p95=130.0,
        mean_terminal=106.0, std_terminal=12.0, cached=False,
    )


class TestFetchMonteCarlo:
    @pytest.mark.asyncio
    async def test_returns_summary_on_success(self):
        summary = _make_mc_summary()
        session = AsyncMock()
        with patch(
            "features.strategy_builder.orchestrator.get_or_run_merton_for_asset",
            new=AsyncMock(return_value=summary),
        ):
            result, err = await _fetch_monte_carlo(session, asset_id=10)
        assert result.prob_positive_return == 0.62
        assert err is None

    @pytest.mark.asyncio
    async def test_returns_error_string_on_failure(self):
        session = AsyncMock()
        with patch(
            "features.strategy_builder.orchestrator.get_or_run_merton_for_asset",
            new=AsyncMock(side_effect=ValueError("insufficient data")),
        ):
            result, err = await _fetch_monte_carlo(session, asset_id=10)
        assert result is None
        assert "insufficient data" in err


class TestFetchAIAgents:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_analysis(self):
        session = AsyncMock()
        with patch(
            "features.strategy_builder.orchestrator.get_latest_agent_analysis",
            new=AsyncMock(return_value=None),
        ):
            result, err = await _fetch_ai_agents(session, asset_id=10)
        assert result is None
        assert err is None

    @pytest.mark.asyncio
    async def test_returns_summary_when_present(self):
        ai = AIAgentSummary(
            analysis_id=1, bias="bullish", conviction_score=0.8,
            sentiment_score=0.6, macro_score=None,
        )
        session = AsyncMock()
        with patch(
            "features.strategy_builder.orchestrator.get_latest_agent_analysis",
            new=AsyncMock(return_value=ai),
        ):
            result, err = await _fetch_ai_agents(session, asset_id=10)
        assert result.conviction_score == 0.8
        assert err is None


class TestFetchFinancials:
    @pytest.mark.asyncio
    async def test_returns_financials_summary(self):
        fin = FinancialsSummary(pe_ttm=25.0, market_cap=2e12)
        session = AsyncMock()
        with patch(
            "features.strategy_builder.orchestrator.get_financials_for_asset",
            new=AsyncMock(return_value=fin),
        ):
            result, err = await _fetch_financials(session, asset_id=10, symbol="AAPL")
        assert result.pe_ttm == 25.0
        assert err is None

    @pytest.mark.asyncio
    async def test_captures_error(self):
        session = AsyncMock()
        with patch(
            "features.strategy_builder.orchestrator.get_financials_for_asset",
            new=AsyncMock(side_effect=Exception("network error")),
        ):
            result, err = await _fetch_financials(session, asset_id=10, symbol="AAPL")
        assert result is None
        assert "network error" in err


class TestFetchAlgoStrategies:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_links(self):
        session = AsyncMock()
        with patch(
            "features.strategy_builder.orchestrator.get_linked_algos",
            new=AsyncMock(return_value=[]),
        ):
            result = await _fetch_algo_strategies(session, strategy_id=1)
        assert result == []

    @pytest.mark.asyncio
    async def test_maps_rows_to_algo_summaries(self):
        row = {
            "algo_attachment_id": 5, "added_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "strategy_name": "ma_crossover", "params": None,
        }
        session = AsyncMock()
        with patch(
            "features.strategy_builder.orchestrator.get_linked_algos",
            new=AsyncMock(return_value=[row]),
        ):
            result = await _fetch_algo_strategies(session, strategy_id=1)
        assert len(result) == 1
        assert result[0].algo_attachment_id == 5
        assert result[0].strategy_name == "ma_crossover"
        assert result[0].params is None

    @pytest.mark.asyncio
    async def test_passes_combo_params_through(self):
        combo_params = {
            "combination_mode": "majority",
            "strategies": [
                {"strategy_name": "rsi", "strategy_params": {}, "weight": 1.0},
                {"strategy_name": "macd", "strategy_params": {}, "weight": 1.0},
            ],
        }
        row = {
            "algo_attachment_id": 9, "added_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "strategy_name": "combo:majority", "params": combo_params,
        }
        session = AsyncMock()
        with patch(
            "features.strategy_builder.orchestrator.get_linked_algos",
            new=AsyncMock(return_value=[row]),
        ):
            result = await _fetch_algo_strategies(session, strategy_id=1)
        assert len(result) == 1
        assert result[0].strategy_name == "combo:majority"
        assert result[0].params == combo_params
        assert result[0].params["combination_mode"] == "majority"
        assert len(result[0].params["strategies"]) == 2


class TestBuildFullStrategyResponse:
    @pytest.mark.asyncio
    async def test_returns_full_response_with_all_sections(self):
        strategy = _make_strategy()
        mc = _make_mc_summary()
        fin = FinancialsSummary(pe_ttm=20.0)
        session = AsyncMock()

        with patch("features.strategy_builder.orchestrator.get_or_run_merton_for_asset", new=AsyncMock(return_value=mc)), \
             patch("features.strategy_builder.orchestrator.get_latest_agent_analysis", new=AsyncMock(return_value=None)), \
             patch("features.strategy_builder.orchestrator.get_financials_for_asset", new=AsyncMock(return_value=fin)), \
             patch("features.strategy_builder.orchestrator.get_linked_algos", new=AsyncMock(return_value=[])):
            result = await build_full_strategy_response(session, strategy, "AAPL", "Apple")

        assert result.strategy_id == 1
        assert result.symbol == "AAPL"
        assert result.monte_carlo.prob_positive_return == 0.62
        assert result.financials.pe_ttm == 20.0
        assert result.ai_agents is None
        assert result.algo_strategies == []
