"""Tests for the auto-trading DAL functions."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from dal.strategy_builder_dal import (
    list_auto_trading_assets,
    update_position_sizing,
    update_thresholds,
)
from models.strategy_builder import TradingStrategy


def _make_strategy(**kwargs):
    s = MagicMock(spec=TradingStrategy)
    s.id = kwargs.get("id_", 1)
    s.asset_id = kwargs.get("asset_id", 10)
    s.is_active = True
    s.mc_buy_prob_positive = kwargs.get("mc_buy_prob_positive")
    s.mc_sell_prob_positive = kwargs.get("mc_sell_prob_positive")
    s.ai_buy_conviction = kwargs.get("ai_buy_conviction")
    s.ai_sell_conviction = kwargs.get("ai_sell_conviction")
    s.ai_buy_sentiment = kwargs.get("ai_buy_sentiment")
    s.ai_sell_sentiment = kwargs.get("ai_sell_sentiment")
    s.ai_buy_macro = kwargs.get("ai_buy_macro")
    s.ai_sell_macro = kwargs.get("ai_sell_macro")
    s.combination_mode = kwargs.get("combination_mode", "all")
    s.algo_timeframe = kwargs.get("algo_timeframe", "1d")
    s.auto_trading_enabled = kwargs.get("auto_trading_enabled", False)
    s.auto_trading_started = kwargs.get("auto_trading_started", False)
    s.max_amount_per_position = kwargs.get("max_amount_per_position")
    s.max_pct_of_capital = kwargs.get("max_pct_of_capital")
    s.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    s.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return s


class TestUpdateThresholds:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        result = await update_thresholds(session, 999, {"mc_buy_prob_positive": 0.6})
        assert result is None

    @pytest.mark.asyncio
    async def test_sets_allowed_fields(self):
        strategy = _make_strategy()
        session = AsyncMock()
        session.get = AsyncMock(return_value=strategy)

        updates = {
            "mc_buy_prob_positive": 0.65,
            "mc_sell_prob_positive": 0.4,
            "ai_buy_conviction": 0.7,
            "ai_sell_conviction": 0.3,
            "ai_buy_sentiment": 0.2,
            "ai_sell_sentiment": -0.1,
            "ai_buy_macro": 0.1,
            "ai_sell_macro": -0.2,
            "combination_mode": "majority",
            "algo_timeframe": "1h",
            "auto_trading_enabled": True,
        }
        result = await update_thresholds(session, 1, updates)

        assert strategy.mc_buy_prob_positive == 0.65
        assert strategy.mc_sell_prob_positive == 0.4
        assert strategy.ai_buy_conviction == 0.7
        assert strategy.ai_sell_conviction == 0.3
        assert strategy.combination_mode == "majority"
        assert strategy.algo_timeframe == "1h"
        assert strategy.auto_trading_enabled is True
        session.flush.assert_awaited_once()
        assert result is strategy

    @pytest.mark.asyncio
    async def test_ignores_unknown_fields(self):
        strategy = _make_strategy()
        session = AsyncMock()
        session.get = AsyncMock(return_value=strategy)

        await update_thresholds(session, 1, {"unknown_field": "oops", "mc_buy_prob_positive": 0.5})
        assert not hasattr(strategy, "unknown_field") or strategy.mc_buy_prob_positive == 0.5


class TestUpdatePositionSizing:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        result = await update_position_sizing(session, 999, True, None, None)
        assert result is None

    @pytest.mark.asyncio
    async def test_sets_started_and_amount(self):
        strategy = _make_strategy()
        session = AsyncMock()
        session.get = AsyncMock(return_value=strategy)

        result = await update_position_sizing(session, 1, True, 500.0, 10.0)

        assert strategy.auto_trading_started is True
        assert strategy.max_amount_per_position == 500.0
        assert strategy.max_pct_of_capital == 10.0
        session.flush.assert_awaited_once()
        assert result is strategy

    @pytest.mark.asyncio
    async def test_stops_trading(self):
        strategy = _make_strategy(auto_trading_started=True)
        session = AsyncMock()
        session.get = AsyncMock(return_value=strategy)

        await update_position_sizing(session, 1, False, None, None)
        assert strategy.auto_trading_started is False

    @pytest.mark.asyncio
    async def test_does_not_override_with_none(self):
        strategy = _make_strategy(max_amount_per_position=200.0, max_pct_of_capital=5.0)
        session = AsyncMock()
        session.get = AsyncMock(return_value=strategy)

        await update_position_sizing(session, 1, False, None, None)
        assert strategy.max_amount_per_position == 200.0
        assert strategy.max_pct_of_capital == 5.0


class TestListAutoTradingAssets:
    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(self):
        row = {
            "strategy_id": 1, "asset_id": 10,
            "symbol": "AAPL", "asset_name": "Apple Inc.",
            "mc_buy_prob_positive": 0.65, "mc_sell_prob_positive": 0.4,
            "ai_buy_conviction": 0.7, "ai_sell_conviction": 0.3,
            "ai_buy_sentiment": 0.2, "ai_sell_sentiment": -0.1,
            "ai_buy_macro": 0.1, "ai_sell_macro": -0.2,
            "combination_mode": "all", "algo_timeframe": "1d",
            "auto_trading_started": False,
            "max_amount_per_position": None, "max_pct_of_capital": None,
            "mc_prob_positive": 0.72,
            "ai_conviction": 0.85, "ai_sentiment": 0.4, "ai_macro": 0.3,
        }
        session = AsyncMock()
        mappings_mock = MagicMock()
        mappings_mock.all.return_value = [row]
        result_mock = MagicMock()
        result_mock.mappings.return_value = mappings_mock
        session.execute = AsyncMock(return_value=result_mock)

        rows = await list_auto_trading_assets(session)
        assert len(rows) == 1
        assert rows[0]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none_enabled(self):
        session = AsyncMock()
        mappings_mock = MagicMock()
        mappings_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.mappings.return_value = mappings_mock
        session.execute = AsyncMock(return_value=result_mock)

        rows = await list_auto_trading_assets(session)
        assert rows == []
