from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from features.execution.order_sync import sync_deployment_orders


@pytest.mark.asyncio
async def test_sync_deployment_orders_updates_status(monkeypatch):
    deployment_id = uuid4()
    order_id = uuid4()
    orders = [
        {
            "id": order_id,
            "alpaca_order_id": "alpaca-1",
            "status": "accepted",
        }
    ]

    monkeypatch.setattr(
        "features.execution.order_sync.execution_order_dal.list_syncable_orders",
        AsyncMock(return_value=orders),
    )
    monkeypatch.setattr(
        "features.execution.order_sync.alpaca_client.get_order",
        AsyncMock(
            return_value={
                "status": "filled",
                "filled_avg_price": 150.0,
                "filled_at": "2024-01-02T15:00:00Z",
                "filled_qty": 2,
                "qty": 2,
            }
        ),
    )
    update_mock = AsyncMock()
    monkeypatch.setattr(
        "features.execution.order_sync.execution_order_dal.update_order_status",
        update_mock,
    )

    updated = await sync_deployment_orders(AsyncMock(), deployment_id)
    assert updated == 1
    update_mock.assert_awaited_once()
