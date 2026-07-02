from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from features.execution.orchestrator import delete_deployment


@pytest.mark.asyncio
async def test_delete_deployment_removes_draft(monkeypatch):
    deployment_id = uuid4()
    deployment = {"id": deployment_id, "symbol": "AAPL", "status": "draft"}
    session = AsyncMock()
    monkeypatch.setattr(
        "features.execution.orchestrator._ensure_trading_enabled",
        lambda: None,
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.get_deployment",
        AsyncMock(return_value=deployment),
    )
    delete_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.delete_deployment",
        delete_mock,
    )

    result = await delete_deployment(session, deployment_id, close_positions=False)
    assert result["deleted"] is True
    assert result["closed_qty"] == 0
    delete_mock.assert_awaited_once_with(session, deployment_id)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_deployment_stops_active_first(monkeypatch):
    deployment_id = uuid4()
    deployment = {"id": deployment_id, "symbol": "AAPL", "status": "active"}
    session = AsyncMock()
    monkeypatch.setattr("features.execution.orchestrator._ensure_trading_enabled", lambda: None)
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.get_deployment",
        AsyncMock(return_value=deployment),
    )
    update_mock = AsyncMock()
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.update_deployment_status",
        update_mock,
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.delete_deployment",
        AsyncMock(return_value=True),
    )

    await delete_deployment(session, deployment_id, close_positions=False)
    update_mock.assert_awaited_once_with(session, deployment_id, status="stopped")


@pytest.mark.asyncio
async def test_delete_deployment_closes_positions_when_requested(monkeypatch):
    deployment_id = uuid4()
    close_order_id = uuid4()
    deployment = {"id": deployment_id, "symbol": "AAPL", "status": "stopped"}
    session = AsyncMock()
    monkeypatch.setattr("features.execution.orchestrator._ensure_trading_enabled", lambda: None)
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.get_deployment",
        AsyncMock(return_value=deployment),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.close_deployment_position",
        AsyncMock(return_value={"closed": True, "qty": 1.25, "order_id": close_order_id}),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.delete_deployment",
        AsyncMock(return_value=True),
    )

    result = await delete_deployment(session, deployment_id, close_positions=True)
    assert result["close_positions"] is True
    assert result["closed_qty"] == 1.25
    assert result["close_order_id"] == close_order_id
    assert result["close_warning"] is None


@pytest.mark.asyncio
async def test_delete_deployment_propagates_close_warning(monkeypatch):
    deployment_id = uuid4()
    deployment = {"id": deployment_id, "symbol": "BTC-USD", "status": "stopped"}
    session = AsyncMock()
    monkeypatch.setattr("features.execution.orchestrator._ensure_trading_enabled", lambda: None)
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.get_deployment",
        AsyncMock(return_value=deployment),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.close_deployment_position",
        AsyncMock(
            return_value={
                "closed": False,
                "qty": 0.0,
                "order_id": None,
                "close_warning": "No BTC-USD position in Alpaca; deployment removed without selling.",
            }
        ),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.delete_deployment",
        AsyncMock(return_value=True),
    )

    result = await delete_deployment(session, deployment_id, close_positions=True)
    assert result["close_warning"] == (
        "No BTC-USD position in Alpaca; deployment removed without selling."
    )


@pytest.mark.asyncio
async def test_delete_deployment_rolls_back_when_close_fails(monkeypatch):
    deployment_id = uuid4()
    deployment = {"id": deployment_id, "symbol": "AAPL", "status": "stopped"}
    session = AsyncMock()
    monkeypatch.setattr("features.execution.orchestrator._ensure_trading_enabled", lambda: None)
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.get_deployment",
        AsyncMock(return_value=deployment),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.close_deployment_position",
        AsyncMock(side_effect=ValueError("Open order pending for this deployment")),
    )
    delete_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.delete_deployment",
        delete_mock,
    )

    with pytest.raises(ValueError, match="Open order pending"):
        await delete_deployment(session, deployment_id, close_positions=True)

    delete_mock.assert_not_awaited()
    session.rollback.assert_awaited_once()
