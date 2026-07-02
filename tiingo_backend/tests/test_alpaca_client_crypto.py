from unittest.mock import AsyncMock, patch

import pytest

from features.execution.alpaca_client import submit_market_order


@pytest.mark.asyncio
async def test_submit_market_order_crypto_payload():
    captured: dict = {}

    async def fake_request(method, path, *, json=None):
        captured["json"] = json
        return {
            "id": "ord-1",
            "symbol": "BTC/USD",
            "side": "buy",
            "qty": "0.5",
            "status": "accepted",
            "submitted_at": "2026-05-28T12:00:00Z",
        }

    with patch(
        "features.execution.alpaca_client._request",
        new=AsyncMock(side_effect=fake_request),
    ):
        result = await submit_market_order("BTC-USD", 0.5, "buy", asset_type="crypto")

    assert captured["json"]["symbol"] == "BTC/USD"
    assert captured["json"]["asset_class"] == "crypto"
    assert captured["json"]["time_in_force"] == "gtc"
    assert captured["json"]["qty"] == "0.5"
    assert result["symbol"] == "BTC/USD"


@pytest.mark.asyncio
async def test_submit_market_order_crypto_buy_rounds_qty_to_two_decimals():
    captured: dict = {}

    async def fake_request(method, path, *, json=None):
        captured["json"] = json
        return {
            "id": "ord-3",
            "symbol": "BTC/USD",
            "side": "buy",
            "qty": "0.07",
            "status": "accepted",
            "submitted_at": "2026-05-28T12:00:00Z",
        }

    with patch(
        "features.execution.alpaca_client._request",
        new=AsyncMock(side_effect=fake_request),
    ):
        await submit_market_order("BTC-USD", 0.0674187, "buy", asset_type="crypto")

    assert captured["json"]["qty"] == "0.07"


@pytest.mark.asyncio
async def test_submit_market_order_crypto_sell_floors_qty():
    captured: dict = {}

    async def fake_request(method, path, *, json=None):
        captured["json"] = json
        return {
            "id": "ord-2",
            "symbol": "BTC/USD",
            "side": "sell",
            "qty": "0.067409372",
            "status": "accepted",
            "submitted_at": "2026-05-28T12:00:00Z",
        }

    with patch(
        "features.execution.alpaca_client._request",
        new=AsyncMock(side_effect=fake_request),
    ):
        await submit_market_order("BTC-USD", 0.0676, "sell", asset_type="crypto")

    assert captured["json"]["qty"] == "0.0676"
