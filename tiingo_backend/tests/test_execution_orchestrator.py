from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from features.execution.orchestrator import activate_deployment


@pytest.mark.asyncio
async def test_activate_allows_multiple_deployments_same_symbol(monkeypatch):
    deployment_id = uuid4()
    model_id = uuid4()
    deployment = {
        "id": deployment_id,
        "model_id": model_id,
        "symbol": "AAPL",
        "trading_mode": "paper",
        "status": "draft",
    }

    monkeypatch.setattr(
        "features.execution.orchestrator._ensure_trading_enabled",
        lambda: None,
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.get_deployment",
        AsyncMock(return_value=deployment),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator._validate_model_for_deployment",
        AsyncMock(return_value={"id": model_id}),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.update_deployment_status",
        AsyncMock(return_value=deployment),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.get_deployment",
        AsyncMock(return_value={**deployment, "status": "active"}),
    )

    result = await activate_deployment(AsyncMock(), deployment_id)
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_evaluate_allows_error_status_deployment(monkeypatch):
    deployment_id = uuid4()
    deployment = {
        "id": deployment_id,
        "model_id": uuid4(),
        "symbol": "MSFT",
        "timeframe": "1d",
        "status": "error",
        "hyperparams_snapshot": {},
    }

    monkeypatch.setattr(
        "features.execution.orchestrator._ensure_trading_enabled",
        lambda: None,
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.trading_deployment_dal.get_deployment",
        AsyncMock(return_value=deployment),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.instrument_dal.get_by_symbol",
        AsyncMock(return_value={"asset_type": "stock"}),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.sync_deployment_orders",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.execution_order_dal.sum_filled_qty_by_deployment",
        AsyncMock(return_value=0),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.refresh_single_deployment_ohlcv",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.run_live_inference",
        AsyncMock(
            return_value={
                "signal": "hold",
                "bar_time": datetime(2026, 5, 28, tzinfo=timezone.utc),
            }
        ),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.record_evaluation",
        AsyncMock(return_value={"id": uuid4()}),
    )

    from features.execution.orchestrator import evaluate_deployment

    result = await evaluate_deployment(AsyncMock(), deployment_id)
    assert result["signal"] == "hold"
