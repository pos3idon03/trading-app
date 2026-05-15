"""Tests for the strategy builder DAL layer."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dal.strategy_builder_dal import (
    attach_algo,
    create_strategy,
    detach_algo,
    get_or_create_strategy,
    get_strategy,
    get_strategy_by_asset,
    list_strategies,
)
from models.strategy_builder import StrategyBacktest, TradingStrategy


def _make_strategy(id_=1, asset_id=10):
    s = MagicMock(spec=TradingStrategy)
    s.id = id_
    s.asset_id = asset_id
    s.is_active = True
    s.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    s.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return s


class TestCreateStrategy:
    @pytest.mark.asyncio
    async def test_adds_and_flushes(self):
        session = AsyncMock()
        strategy = await create_strategy(session, asset_id=5)
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_trading_strategy_instance(self):
        session = AsyncMock()
        result = await create_strategy(session, asset_id=5)
        assert isinstance(result, TradingStrategy)
        assert result.asset_id == 5
        assert result.is_active is True


class TestGetOrCreateStrategy:
    @pytest.mark.asyncio
    async def test_returns_existing_when_found(self):
        existing = _make_strategy(id_=7, asset_id=10)
        session = AsyncMock()
        with patch("dal.strategy_builder_dal.get_strategy_by_asset", new=AsyncMock(return_value=existing)):
            result = await get_or_create_strategy(session, asset_id=10)
        assert result.id == 7

    @pytest.mark.asyncio
    async def test_creates_when_not_found(self):
        session = AsyncMock()
        with patch("dal.strategy_builder_dal.get_strategy_by_asset", new=AsyncMock(return_value=None)), \
             patch("dal.strategy_builder_dal.create_strategy", new=AsyncMock(return_value=_make_strategy(id_=99))):
            result = await get_or_create_strategy(session, asset_id=10)
        assert result.id == 99


class TestGetStrategy:
    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_id(self):
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        result = await get_strategy(session, 999)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_strategy_when_found(self):
        strategy = _make_strategy(id_=3)
        session = AsyncMock()
        session.get = AsyncMock(return_value=strategy)
        result = await get_strategy(session, 3)
        assert result.id == 3


class TestGetStrategyByAsset:
    @pytest.mark.asyncio
    async def test_returns_none_when_absent(self):
        session = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.first.return_value = None
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=execute_result)

        result = await get_strategy_by_asset(session, asset_id=42)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_strategy_when_present(self):
        strategy = _make_strategy(id_=5, asset_id=42)
        session = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.first.return_value = strategy
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=execute_result)

        result = await get_strategy_by_asset(session, asset_id=42)
        assert result.id == 5


class TestListStrategies:
    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(self):
        row = {"strategy_id": 1, "asset_id": 10, "is_active": True,
               "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1),
               "symbol": "AAPL", "asset_name": "Apple"}
        session = AsyncMock()
        mappings_mock = MagicMock()
        mappings_mock.all.return_value = [row]
        result_mock = MagicMock()
        result_mock.mappings.return_value = mappings_mock
        session.execute = AsyncMock(return_value=result_mock)

        rows = await list_strategies(session)
        assert len(rows) == 1
        assert rows[0]["symbol"] == "AAPL"


class TestAttachDetachAlgo:
    @pytest.mark.asyncio
    async def test_attach_executes_upsert(self):
        session = AsyncMock()
        link = MagicMock(spec=StrategyBacktest)
        link.strategy_id = 1
        link.strategy_name = "ma_crossover"
        scalars_mock = MagicMock()
        scalars_mock.first.return_value = link
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=execute_result)

        result = await attach_algo(session, strategy_id=1, strategy_name="ma_crossover", params={})
        assert session.execute.called

    @pytest.mark.asyncio
    async def test_detach_returns_false_when_not_found(self):
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        result = await detach_algo(session, strategy_id=1, algo_attachment_id=99)
        assert result is False

    @pytest.mark.asyncio
    async def test_detach_returns_false_when_wrong_strategy(self):
        link = MagicMock(spec=StrategyBacktest)
        link.strategy_id = 2  # different strategy_id
        session = AsyncMock()
        session.get = AsyncMock(return_value=link)

        result = await detach_algo(session, strategy_id=1, algo_attachment_id=5)
        assert result is False

    @pytest.mark.asyncio
    async def test_detach_returns_true_when_found(self):
        link = MagicMock(spec=StrategyBacktest)
        link.strategy_id = 1
        session = AsyncMock()
        session.get = AsyncMock(return_value=link)

        result = await detach_algo(session, strategy_id=1, algo_attachment_id=5)
        assert result is True
        session.delete.assert_awaited_once_with(link)
