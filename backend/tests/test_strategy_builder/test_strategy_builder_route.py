"""Tests for the strategy builder route handlers."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from dtos.strategy_builder_dto import AttachAlgoRequest, CreateStrategyRequest
from models.strategy_builder import TradingStrategy


def _make_strategy(id_=1, asset_id=10):
    s = MagicMock(spec=TradingStrategy)
    s.id = id_
    s.asset_id = asset_id
    s.is_active = True
    s.mc_buy_prob_positive = None
    s.mc_sell_prob_positive = None
    s.ai_buy_conviction = None
    s.ai_sell_conviction = None
    s.ai_buy_sentiment = None
    s.ai_sell_sentiment = None
    s.ai_buy_macro = None
    s.ai_sell_macro = None
    s.combination_mode = "all"
    s.algo_timeframe = "1d"
    s.auto_trading_enabled = False
    s.auto_trading_started = False
    s.max_amount_per_position = None
    s.max_pct_of_capital = None
    s.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    s.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return s


def _make_asset_info(id_=10, symbol="AAPL", name="Apple Inc."):
    return {"id": id_, "symbol": symbol, "name": name,
            "asset_type": "stock", "exchange": "NASDAQ",
            "currency": "USD", "is_active": True}


class TestCreateStrategyCard:
    @pytest.mark.asyncio
    async def test_raises_409_when_already_exists(self):
        from routes.strategy_builder import create_strategy_card

        session = AsyncMock()
        with patch("routes.strategy_builder.get_strategy_by_asset", new=AsyncMock(return_value=_make_strategy())):
            with pytest.raises(HTTPException) as exc:
                await create_strategy_card(CreateStrategyRequest(asset_id=10), session)
            assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_creates_and_returns_record(self):
        from routes.strategy_builder import create_strategy_card

        session = AsyncMock()
        with patch("routes.strategy_builder.get_strategy_by_asset", new=AsyncMock(return_value=None)), \
             patch("routes.strategy_builder.create_strategy", new=AsyncMock(return_value=_make_strategy())), \
             patch("routes.strategy_builder._get_asset_info", new=AsyncMock(return_value=_make_asset_info())):
            result = await create_strategy_card(CreateStrategyRequest(asset_id=10), session)

        assert result.asset_id == 10
        assert result.symbol == "AAPL"


class TestListStrategyCards:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        from routes.strategy_builder import list_strategy_cards

        session = AsyncMock()
        with patch("routes.strategy_builder.list_strategies", new=AsyncMock(return_value=[])):
            result = await list_strategy_cards(session)
        assert result == []

    @pytest.mark.asyncio
    async def test_maps_rows_to_records(self):
        from routes.strategy_builder import list_strategy_cards

        row = {
            "strategy_id": 1, "asset_id": 10, "is_active": True,
            "mc_buy_prob_positive": None, "mc_sell_prob_positive": None,
            "ai_buy_conviction": None, "ai_sell_conviction": None,
            "ai_buy_sentiment": None, "ai_sell_sentiment": None,
            "ai_buy_macro": None, "ai_sell_macro": None,
            "combination_mode": "all", "algo_timeframe": "1d",
            "auto_trading_enabled": False, "auto_trading_started": False,
            "max_amount_per_position": None, "max_pct_of_capital": None,
            "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "symbol": "AAPL", "asset_name": "Apple",
        }
        session = AsyncMock()
        with patch("routes.strategy_builder.list_strategies", new=AsyncMock(return_value=[row])):
            result = await list_strategy_cards(session)

        assert len(result) == 1
        assert result[0].symbol == "AAPL"


class TestGetFullStrategy:
    @pytest.mark.asyncio
    async def test_raises_404_when_missing(self):
        from routes.strategy_builder import get_full_strategy

        session = AsyncMock()
        with patch("routes.strategy_builder.get_strategy", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc:
                await get_full_strategy(999, session)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_calls_orchestrator(self):
        from routes.strategy_builder import get_full_strategy
        from dtos.strategy_builder_dto import StrategyFullResponse

        strategy = _make_strategy()
        mock_response = MagicMock(spec=StrategyFullResponse)
        session = AsyncMock()

        with patch("routes.strategy_builder.get_strategy", new=AsyncMock(return_value=strategy)), \
             patch("routes.strategy_builder._get_asset_info", new=AsyncMock(return_value=_make_asset_info())), \
             patch("routes.strategy_builder.build_full_strategy_response", new=AsyncMock(return_value=mock_response)):
            result = await get_full_strategy(1, session)

        assert result is mock_response


class TestAttachAlgo:
    @pytest.mark.asyncio
    async def test_auto_creates_strategy_and_links(self):
        from routes.strategy_builder import attach_algo_to_strategy

        strategy = _make_strategy()
        session = AsyncMock()

        with patch("routes.strategy_builder.get_or_create_strategy", new=AsyncMock(return_value=strategy)), \
             patch("routes.strategy_builder.attach_algo", new=AsyncMock()), \
             patch("routes.strategy_builder.sync_algo_timeframe_from_attachments", new=AsyncMock()), \
             patch("routes.strategy_builder._get_asset_info", new=AsyncMock(return_value=_make_asset_info())):
            result = await attach_algo_to_strategy(
                AttachAlgoRequest(
                    asset_id=10,
                    strategy_name="ma_crossover",
                    params={},
                    timeframe="30m",
                ),
                session,
            )

        assert result.id == 1
        assert result.symbol == "AAPL"


class TestDeleteStrategy:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        from routes.strategy_builder import delete_strategy_card

        session = AsyncMock()
        with patch("routes.strategy_builder.delete_strategy", new=AsyncMock(return_value=False)):
            with pytest.raises(HTTPException) as exc:
                await delete_strategy_card(999, session)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_deleted_true(self):
        from routes.strategy_builder import delete_strategy_card

        session = AsyncMock()
        with patch("routes.strategy_builder.delete_strategy", new=AsyncMock(return_value=True)):
            result = await delete_strategy_card(1, session)
        assert result == {"deleted": True}
