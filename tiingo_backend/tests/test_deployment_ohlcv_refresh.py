from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from features.ingestion.deployment_ohlcv_refresh import (
    build_deployment_fetch_plan,
    build_fetch_targets,
    refresh_deployment_ohlcv,
)


@pytest.mark.asyncio
async def test_build_deployment_fetch_plan_empty_when_no_active(monkeypatch):
    monkeypatch.setattr(
        "features.ingestion.deployment_ohlcv_refresh.trading_deployment_dal.list_active_deployment_requirements",
        AsyncMock(return_value=[]),
    )
    plan = await build_deployment_fetch_plan(AsyncMock())
    assert plan.is_empty


def test_build_fetch_targets_deduplicates_and_maps_4h():
    requirements = [
        {"symbol": "AAPL", "timeframe": "5m", "asset_type": "stock"},
        {"symbol": "AAPL", "timeframe": "5m", "asset_type": "stock"},
        {"symbol": "MSFT", "timeframe": "4h", "asset_type": "stock"},
    ]
    plan = build_fetch_targets(requirements)
    assert len(plan.targets) == 2
    assert plan.derive_4h_symbols == {"MSFT"}
    msft = next(target for target in plan.targets if target.symbol == "MSFT")
    assert msft.native_timeframe == "1h"
    assert msft.source == "tiingo_iex"


def test_build_fetch_targets_crypto_intraday_uses_alpaca():
    plan = build_fetch_targets(
        [{"symbol": "BTC-USD", "timeframe": "1h", "asset_type": "crypto"}],
    )
    assert len(plan.targets) == 1
    assert plan.targets[0].source == "alpaca_crypto"
    assert plan.targets[0].native_timeframe == "1h"


@pytest.mark.asyncio
async def test_refresh_deployment_ohlcv_noop_on_empty_plan():
    results = await refresh_deployment_ohlcv(AsyncMock(), build_fetch_targets([]))
    assert results == []


@pytest.mark.asyncio
async def test_refresh_deployment_ohlcv_calls_incremental_backfill(monkeypatch):
    requirements = [{"symbol": "AAPL", "timeframe": "5m", "asset_type": "stock"}]
    plan = build_fetch_targets(requirements)
    backfill = AsyncMock(return_value=(3, None))
    monkeypatch.setattr(
        "features.ingestion.deployment_ohlcv_refresh.incremental_backfill_symbol_timeframe",
        backfill,
    )
    monkeypatch.setattr(
        "features.ingestion.deployment_ohlcv_refresh.instrument_dal.get_by_symbol",
        AsyncMock(return_value={"id": 1, "asset_type": "stock", "tiingo_ticker": "AAPL"}),
    )

    results = await refresh_deployment_ohlcv(AsyncMock(), plan)
    assert results[0]["status"] == "ok"
    assert results[0]["inserted"] == 3
    backfill.assert_awaited_once()
    assert backfill.await_args.kwargs["derive_4h"] is False


@pytest.mark.asyncio
async def test_refresh_deployment_ohlcv_derives_4h(monkeypatch):
    requirements = [{"symbol": "AAPL", "timeframe": "4h", "asset_type": "stock"}]
    plan = build_fetch_targets(requirements)
    backfill = AsyncMock(return_value=(2, None))
    monkeypatch.setattr(
        "features.ingestion.deployment_ohlcv_refresh.incremental_backfill_symbol_timeframe",
        backfill,
    )
    monkeypatch.setattr(
        "features.ingestion.deployment_ohlcv_refresh.instrument_dal.get_by_symbol",
        AsyncMock(return_value={"id": 1, "asset_type": "stock", "tiingo_ticker": "AAPL"}),
    )

    await refresh_deployment_ohlcv(AsyncMock(), plan)
    assert backfill.await_args.kwargs["derive_4h"] is True


@pytest.mark.asyncio
async def test_build_deployment_fetch_plan_filters_timeframe(monkeypatch):
    monkeypatch.setattr(
        "features.ingestion.deployment_ohlcv_refresh.trading_deployment_dal.list_active_deployment_requirements",
        AsyncMock(
            return_value=[
                {"symbol": "AAPL", "timeframe": "5m", "asset_type": "stock"},
                {"symbol": "MSFT", "timeframe": "1d", "asset_type": "stock"},
            ],
        ),
    )
    plan = await build_deployment_fetch_plan(AsyncMock(), deployment_timeframes={"5m"})
    assert len(plan.targets) == 1
    assert plan.targets[0].symbol == "AAPL"
