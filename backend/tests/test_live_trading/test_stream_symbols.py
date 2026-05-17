"""Tests for live stream symbol resolution."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from features.live_trading.stream_symbols import build_stream_plan


@pytest.mark.asyncio
async def test_btc_usd_maps_to_crypto_channel():
    with patch(
        "features.live_trading.stream_symbols.get_asset_type_by_symbol",
        new=AsyncMock(return_value="crypto"),
    ):
        plan = await build_stream_plan(None, ["BTC-USD"])
    assert len(plan.entries) == 1
    assert plan.entries[0].app_symbol == "BTC-USD"
    assert plan.entries[0].alpaca_symbol == "BTC/USD"
    assert plan.entries[0].channel == "crypto"


@pytest.mark.asyncio
async def test_aapl_maps_to_stock_channel():
    with patch(
        "features.live_trading.stream_symbols.get_asset_type_by_symbol",
        new=AsyncMock(return_value="stock"),
    ):
        plan = await build_stream_plan(None, ["AAPL"])
    assert len(plan.entries) == 1
    assert plan.entries[0].channel == "stock"
    assert plan.entries[0].alpaca_symbol == "AAPL"


@pytest.mark.asyncio
async def test_unsupported_symbol_skipped():
    with patch(
        "features.live_trading.stream_symbols.get_asset_type_by_symbol",
        new=AsyncMock(return_value="stock"),
    ):
        plan = await build_stream_plan(None, ["BARC.L"])
    assert plan.entries == []
    assert "BARC.L" in plan.skipped
