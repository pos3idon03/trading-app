from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from features.execution.deployment_close import close_deployment_position


@pytest.mark.asyncio
async def test_close_deployment_position_skips_when_flat(monkeypatch):
    deployment_id = uuid4()
    deployment = {"id": deployment_id, "symbol": "AAPL"}
    monkeypatch.setattr(
        "features.execution.deployment_close.sync_deployment_orders",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "features.execution.deployment_close.execution_order_dal.sum_filled_qty_by_deployment",
        AsyncMock(return_value=0.0),
    )

    result = await close_deployment_position(AsyncMock(), deployment)
    assert result == {"closed": False, "qty": 0.0, "order_id": None}


@pytest.mark.asyncio
async def test_close_deployment_position_sells_net_qty(monkeypatch):
    deployment_id = uuid4()
    order_id = uuid4()
    deployment = {"id": deployment_id, "symbol": "AAPL"}
    monkeypatch.setattr(
        "features.execution.deployment_close.sync_deployment_orders",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "features.execution.deployment_close.execution_order_dal.sum_filled_qty_by_deployment",
        AsyncMock(return_value=2.5),
    )
    monkeypatch.setattr(
        "features.execution.deployment_close.execution_order_dal.has_open_order",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "features.execution.deployment_close.alpaca_client.submit_market_order",
        AsyncMock(return_value={"id": "alpaca-1", "status": "accepted"}),
    )
    monkeypatch.setattr(
        "features.execution.deployment_close.execution_settings_dal.record_order_submission",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "features.execution.deployment_close.execution_order_dal.create_order",
        AsyncMock(return_value={"id": order_id}),
    )

    result = await close_deployment_position(AsyncMock(), deployment)
    assert result["closed"] is True
    assert result["qty"] == 2.5
    assert result["order_id"] == order_id


@pytest.mark.asyncio
async def test_close_deployment_position_blocks_when_open_order(monkeypatch):
    deployment = {"id": uuid4(), "symbol": "AAPL"}
    monkeypatch.setattr(
        "features.execution.deployment_close.sync_deployment_orders",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "features.execution.deployment_close.execution_order_dal.sum_filled_qty_by_deployment",
        AsyncMock(return_value=1.0),
    )
    monkeypatch.setattr(
        "features.execution.deployment_close.execution_order_dal.has_open_order",
        AsyncMock(return_value=True),
    )

    with pytest.raises(ValueError, match="Open order pending"):
        await close_deployment_position(AsyncMock(), deployment)
