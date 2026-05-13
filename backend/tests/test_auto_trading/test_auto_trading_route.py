"""Tests for the auto-trading route handlers."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from dtos.strategy_builder_dto import UpdatePositionSizingRequest
from models.strategy_builder import TradingStrategy


def _make_strategy(id_=1, asset_id=10, **kwargs):
    s = MagicMock(spec=TradingStrategy)
    s.id = id_
    s.asset_id = asset_id
    s.is_active = True
    s.auto_trading_enabled = kwargs.get("auto_trading_enabled", True)
    s.auto_trading_started = kwargs.get("auto_trading_started", False)
    s.combination_mode = kwargs.get("combination_mode", "all")
    s.algo_timeframe = kwargs.get("algo_timeframe", "1d")
    s.max_amount_per_position = kwargs.get("max_amount_per_position")
    s.max_pct_of_capital = kwargs.get("max_pct_of_capital")
    s.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    s.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return s


def _make_row(strategy_id=1, started=False, **kwargs):
    return {
        "strategy_id": strategy_id,
        "asset_id": 10,
        "symbol": "AAPL",
        "asset_name": "Apple Inc.",
        "mc_prob_positive": 0.72,
        "mc_buy_prob_positive": 0.65,
        "mc_sell_prob_positive": 0.4,
        "ai_conviction": 0.85,
        "ai_sentiment": 0.4,
        "ai_macro": 0.3,
        "ai_buy_conviction": 0.7,
        "ai_sell_conviction": 0.3,
        "ai_buy_sentiment": 0.2,
        "ai_sell_sentiment": -0.1,
        "ai_buy_macro": 0.1,
        "ai_sell_macro": -0.2,
        "combination_mode": "all",
        "algo_timeframe": "1d",
        "auto_trading_started": started,
        "max_amount_per_position": kwargs.get("max_amount_per_position"),
        "max_pct_of_capital": kwargs.get("max_pct_of_capital"),
    }


class TestListAutoTrading:
    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none_enabled(self):
        from routes.auto_trading import list_auto_trading

        session = AsyncMock()
        with patch("routes.auto_trading.list_auto_trading_assets", new=AsyncMock(return_value=[])):
            result = await list_auto_trading(session)
        assert result == []

    @pytest.mark.asyncio
    async def test_maps_rows_to_dto(self):
        from routes.auto_trading import list_auto_trading

        session = AsyncMock()
        rows = [_make_row(strategy_id=1)]
        with patch("routes.auto_trading.list_auto_trading_assets", new=AsyncMock(return_value=rows)):
            result = await list_auto_trading(session)

        assert len(result) == 1
        assert result[0].symbol == "AAPL"
        assert result[0].mc_prob_positive == 0.72
        assert result[0].mc_buy_prob_positive == 0.65
        assert result[0].mc_sell_prob_positive == 0.4


class TestStartAutoTrading:
    @pytest.mark.asyncio
    async def test_raises_404_when_strategy_not_found(self):
        from routes.auto_trading import start_auto_trading

        session = AsyncMock()
        with patch("routes.auto_trading.get_strategy", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc:
                await start_auto_trading(
                    999, UpdatePositionSizingRequest(), session
                )
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_409_when_not_enabled(self):
        from routes.auto_trading import start_auto_trading

        strategy = _make_strategy(auto_trading_enabled=False)
        session = AsyncMock()
        with patch("routes.auto_trading.get_strategy", new=AsyncMock(return_value=strategy)):
            with pytest.raises(HTTPException) as exc:
                await start_auto_trading(
                    1, UpdatePositionSizingRequest(), session
                )
            assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_starts_trading_and_returns_row(self):
        from routes.auto_trading import start_auto_trading

        strategy = _make_strategy(auto_trading_enabled=True)
        updated_row = _make_row(strategy_id=1, started=True, max_amount_per_position=500.0)
        session = AsyncMock()

        with patch("routes.auto_trading.get_strategy", new=AsyncMock(return_value=strategy)), \
             patch("routes.auto_trading.update_position_sizing", new=AsyncMock()), \
             patch("routes.auto_trading.list_auto_trading_assets", new=AsyncMock(return_value=[updated_row])):
            result = await start_auto_trading(
                1, UpdatePositionSizingRequest(max_amount_per_position=500.0), session
            )

        assert result.auto_trading_started is True
        assert result.max_amount_per_position == 500.0

    @pytest.mark.asyncio
    async def test_dynamic_sizing_when_no_params(self):
        from routes.auto_trading import start_auto_trading

        strategy = _make_strategy(auto_trading_enabled=True)
        updated_row = _make_row(strategy_id=1, started=True)
        session = AsyncMock()

        with patch("routes.auto_trading.get_strategy", new=AsyncMock(return_value=strategy)), \
             patch("routes.auto_trading.update_position_sizing", new=AsyncMock()) as mock_update, \
             patch("routes.auto_trading.list_auto_trading_assets", new=AsyncMock(return_value=[updated_row])):
            await start_auto_trading(1, UpdatePositionSizingRequest(), session)

        mock_update.assert_awaited_once_with(
            session, strategy_id=1, started=True, max_amount=None, max_pct=None
        )


class TestStopAutoTrading:
    @pytest.mark.asyncio
    async def test_raises_404_when_strategy_not_found(self):
        from routes.auto_trading import stop_auto_trading

        session = AsyncMock()
        with patch("routes.auto_trading.get_strategy", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc:
                await stop_auto_trading(999, session)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_stops_trading_and_returns_row(self):
        from routes.auto_trading import stop_auto_trading

        strategy = _make_strategy(auto_trading_started=True)
        stopped_row = _make_row(strategy_id=1, started=False)
        session = AsyncMock()

        with patch("routes.auto_trading.get_strategy", new=AsyncMock(return_value=strategy)), \
             patch("routes.auto_trading.update_position_sizing", new=AsyncMock()), \
             patch("routes.auto_trading.list_auto_trading_assets", new=AsyncMock(return_value=[stopped_row])):
            result = await stop_auto_trading(1, session)

        assert result.auto_trading_started is False
