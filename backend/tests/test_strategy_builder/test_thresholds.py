"""Tests for the strategy thresholds PATCH endpoint."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from dtos.strategy_builder_dto import UpdateThresholdsRequest
from models.strategy_builder import TradingStrategy


def _make_strategy(id_=1, asset_id=10, **kwargs):
    s = MagicMock(spec=TradingStrategy)
    s.id = id_
    s.asset_id = asset_id
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


def _make_asset_info(id_=10, symbol="AAPL", name="Apple Inc."):
    return {"id": id_, "symbol": symbol, "name": name,
            "asset_type": "stock", "exchange": "NASDAQ",
            "currency": "USD", "is_active": True}


class TestUpdateStrategyThresholds:
    @pytest.mark.asyncio
    async def test_raises_404_when_strategy_not_found(self):
        from routes.strategy_builder import update_strategy_thresholds

        session = AsyncMock()
        with patch("routes.strategy_builder.update_thresholds", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc:
                await update_strategy_thresholds(
                    999, UpdateThresholdsRequest(mc_buy_prob_positive=0.6), session
                )
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_updated_mc_thresholds(self):
        from routes.strategy_builder import update_strategy_thresholds

        strategy = _make_strategy(mc_buy_prob_positive=0.65, mc_sell_prob_positive=0.4)
        session = AsyncMock()

        with patch("routes.strategy_builder.update_thresholds", new=AsyncMock(return_value=strategy)), \
             patch("routes.strategy_builder._get_asset_info", new=AsyncMock(return_value=_make_asset_info())):
            result = await update_strategy_thresholds(
                1,
                UpdateThresholdsRequest(mc_buy_prob_positive=0.65, mc_sell_prob_positive=0.4),
                session,
            )

        assert result.mc_buy_prob_positive == 0.65
        assert result.mc_sell_prob_positive == 0.4
        assert result.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_enables_auto_trading(self):
        from routes.strategy_builder import update_strategy_thresholds

        strategy = _make_strategy(auto_trading_enabled=True)
        session = AsyncMock()

        with patch("routes.strategy_builder.update_thresholds", new=AsyncMock(return_value=strategy)), \
             patch("routes.strategy_builder._get_asset_info", new=AsyncMock(return_value=_make_asset_info())):
            result = await update_strategy_thresholds(
                1, UpdateThresholdsRequest(auto_trading_enabled=True), session
            )

        assert result.auto_trading_enabled is True

    @pytest.mark.asyncio
    async def test_updates_combination_mode(self):
        from routes.strategy_builder import update_strategy_thresholds

        strategy = _make_strategy(combination_mode="majority")
        session = AsyncMock()

        with patch("routes.strategy_builder.update_thresholds", new=AsyncMock(return_value=strategy)), \
             patch("routes.strategy_builder._get_asset_info", new=AsyncMock(return_value=_make_asset_info())):
            result = await update_strategy_thresholds(
                1, UpdateThresholdsRequest(combination_mode="majority"), session
            )

        assert result.combination_mode == "majority"

    @pytest.mark.asyncio
    async def test_updates_algo_timeframe(self):
        from routes.strategy_builder import update_strategy_thresholds

        strategy = _make_strategy(algo_timeframe="1h")
        session = AsyncMock()

        with patch("routes.strategy_builder.update_thresholds", new=AsyncMock(return_value=strategy)), \
             patch("routes.strategy_builder._get_asset_info", new=AsyncMock(return_value=_make_asset_info())):
            result = await update_strategy_thresholds(
                1, UpdateThresholdsRequest(algo_timeframe="1h"), session
            )

        assert result.algo_timeframe == "1h"

    @pytest.mark.asyncio
    async def test_ai_buy_sell_thresholds_returned(self):
        from routes.strategy_builder import update_strategy_thresholds

        strategy = _make_strategy(
            ai_buy_conviction=0.7, ai_sell_conviction=0.3,
            ai_buy_sentiment=0.1, ai_sell_sentiment=-0.2,
            ai_buy_macro=0.0, ai_sell_macro=-0.3,
        )
        session = AsyncMock()

        with patch("routes.strategy_builder.update_thresholds", new=AsyncMock(return_value=strategy)), \
             patch("routes.strategy_builder._get_asset_info", new=AsyncMock(return_value=_make_asset_info())):
            result = await update_strategy_thresholds(
                1,
                UpdateThresholdsRequest(
                    ai_buy_conviction=0.7, ai_sell_conviction=0.3,
                    ai_buy_sentiment=0.1, ai_sell_sentiment=-0.2,
                    ai_buy_macro=0.0, ai_sell_macro=-0.3,
                ),
                session,
            )

        assert result.ai_buy_conviction == 0.7
        assert result.ai_sell_conviction == 0.3
        assert result.ai_buy_sentiment == 0.1
        assert result.ai_sell_sentiment == -0.2
        assert result.ai_buy_macro == 0.0
        assert result.ai_sell_macro == -0.3

    def test_negative_conviction_thresholds_accepted(self):
        req = UpdateThresholdsRequest(
            ai_buy_conviction=0.5, ai_sell_conviction=-0.1,
        )
        assert req.ai_sell_conviction == -0.1

    def test_conviction_out_of_range_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UpdateThresholdsRequest(ai_buy_conviction=1.5)
        with pytest.raises(ValidationError):
            UpdateThresholdsRequest(ai_sell_conviction=-1.1)
