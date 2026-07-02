from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from features.execution.evaluation_cycle import (
    list_deployments_for_evaluation_cycle,
    refresh_active_deployment_market_data,
    run_deployment_cycle,
)
from features.execution.job_runner import execute_execution_job
from utils.json_serialization import json_safe


@pytest.mark.asyncio
async def test_run_deployment_cycle_skips_without_active(monkeypatch):
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.list_deployments_for_evaluation_cycle",
        AsyncMock(return_value=[]),
    )
    result = await run_deployment_cycle(AsyncMock())
    assert result["skipped"] is True
    assert result["reason"] == "no active deployments"


@pytest.mark.asyncio
async def test_run_deployment_cycle_skips_when_no_timeframes_due(monkeypatch):
    deployment_id = uuid4()
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.list_deployments_for_evaluation_cycle",
        AsyncMock(return_value=[
            {"id": deployment_id, "timeframe": "5m", "status": "active", "asset_type": "stock"},
        ]),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle._run_reconciliation",
        AsyncMock(return_value={"catch_up_runs": 0, "results": []}),
    )
    as_of = datetime(2026, 5, 28, 10, 7, tzinfo=timezone.utc)
    result = await run_deployment_cycle(AsyncMock(), as_of=as_of)
    assert result["skipped"] is True
    assert result["reason"] == "no deployments due"


def _evaluation_outcome(deployment_id):
    evaluation_id = uuid4()
    bar_time = datetime(2026, 5, 28, 15, 0, tzinfo=timezone.utc)
    return {
        "deployment_id": deployment_id,
        "skipped": False,
        "evaluation": {
            "id": evaluation_id,
            "deployment_id": deployment_id,
            "bar_time": bar_time,
            "created_at": bar_time,
        },
    }


@pytest.mark.asyncio
async def test_run_deployment_cycle_refreshes_then_evaluates(monkeypatch):
    deployment_id = uuid4()
    deployment = {
        "id": deployment_id,
        "timeframe": "5m",
        "status": "active",
        "asset_type": "stock",
    }
    refresh = AsyncMock(return_value=[{"symbol": "AAPL", "status": "ok"}])
    evaluate = AsyncMock(return_value=_evaluation_outcome(deployment_id))
    build_plan = AsyncMock(return_value=type("Plan", (), {"is_empty": False})())

    monkeypatch.setattr(
        "features.execution.evaluation_cycle.list_deployments_for_evaluation_cycle",
        AsyncMock(return_value=[deployment]),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.build_deployment_fetch_plan",
        build_plan,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.refresh_deployment_ohlcv",
        refresh,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.evaluate_deployment",
        evaluate,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle._run_reconciliation",
        AsyncMock(return_value={"catch_up_runs": 0, "results": []}),
    )

    as_of = datetime(2026, 5, 28, 15, 0, tzinfo=timezone.utc)
    result = await run_deployment_cycle(AsyncMock(), as_of=as_of, force_timeframes={"5m"})

    assert result["skipped"] is False
    assert result["results"][0]["timeframe"] == "5m"
    json.dumps(json_safe(result))
    refresh.assert_awaited_once()
    evaluate.assert_awaited_once()
    assert evaluate.await_args.args[1] == deployment_id


@pytest.mark.asyncio
async def test_refresh_active_deployment_market_data_noop(monkeypatch):
    empty_plan = type("Plan", (), {"is_empty": True})()
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.build_deployment_fetch_plan",
        AsyncMock(return_value=empty_plan),
    )
    result = await refresh_active_deployment_market_data(AsyncMock())
    assert result["skipped"] is True


@pytest.mark.asyncio
async def test_run_deployment_cycle_uses_scheduled_as_of_for_due_timeframes(monkeypatch):
    deployment_id = uuid4()
    deployment = {
        "id": deployment_id,
        "timeframe": "1h",
        "status": "active",
        "asset_type": "stock",
    }
    refresh = AsyncMock(return_value=[{"symbol": "IBM", "status": "ok"}])
    evaluate = AsyncMock(return_value=_evaluation_outcome(deployment_id))
    build_plan = AsyncMock(return_value=type("Plan", (), {"is_empty": False})())
    reconcile = AsyncMock(return_value={"catch_up_runs": 0, "results": []})

    monkeypatch.setattr(
        "features.execution.evaluation_cycle.list_deployments_for_evaluation_cycle",
        AsyncMock(return_value=[deployment]),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.build_deployment_fetch_plan",
        build_plan,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.refresh_deployment_ohlcv",
        refresh,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.evaluate_deployment",
        evaluate,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle._run_reconciliation",
        reconcile,
    )

    scheduled = datetime(2026, 5, 28, 14, 0, tzinfo=timezone.utc)
    result = await run_deployment_cycle(AsyncMock(), as_of=scheduled)

    assert result["skipped"] is False
    assert "1h" in result["timeframes"]
    json.dumps(json_safe(result))
    refresh.assert_awaited_once()
    evaluate.assert_awaited_once()


@pytest.mark.asyncio
async def test_crypto_deployment_due_when_equity_intraday_not(monkeypatch):
    stock_id = uuid4()
    crypto_id = uuid4()
    deployments = [
        {"id": stock_id, "timeframe": "1h", "status": "active", "asset_type": "stock"},
        {"id": crypto_id, "timeframe": "1h", "status": "active", "asset_type": "crypto"},
    ]
    evaluate = AsyncMock(side_effect=lambda _s, dep_id: _evaluation_outcome(dep_id))
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.list_deployments_for_evaluation_cycle",
        AsyncMock(return_value=deployments),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.build_deployment_fetch_plan",
        AsyncMock(return_value=type("Plan", (), {"is_empty": False})()),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.refresh_deployment_ohlcv",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.evaluate_deployment",
        evaluate,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle._run_reconciliation",
        AsyncMock(return_value={"catch_up_runs": 0, "results": []}),
    )

    as_of = datetime(2026, 5, 28, 2, 0, tzinfo=timezone.utc)
    result = await run_deployment_cycle(AsyncMock(), as_of=as_of)
    assert result["skipped"] is False
    assert evaluate.await_count == 1
    assert evaluate.await_args.args[1] == crypto_id


@pytest.mark.asyncio
async def test_list_deployments_for_evaluation_cycle_includes_error_retry(monkeypatch):
    error_id = uuid4()
    active = [{"id": uuid4(), "timeframe": "1h", "status": "active", "asset_type": "stock"}]
    error_dep = {
        "id": error_id,
        "timeframe": "1h",
        "status": "error",
        "asset_type": "crypto",
        "last_signal": "sell",
        "last_outcome": "error",
    }
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.trading_deployment_dal.list_active_deployments_with_instrument",
        AsyncMock(return_value=active),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.trading_deployment_dal.list_error_deployments_with_instrument",
        AsyncMock(return_value=[error_dep]),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.execution_order_dal.sum_filled_qty_by_deployment",
        AsyncMock(return_value=0.5),
    )

    rows = await list_deployments_for_evaluation_cycle(AsyncMock())
    assert len(rows) == 2
    assert any(row["id"] == error_id for row in rows)


@pytest.mark.asyncio
async def test_execute_deployment_cycle_job_uses_scheduled_at_param(monkeypatch):
    run_cycle = AsyncMock(return_value={"skipped": True, "reason": "no deployments due"})
    monkeypatch.setattr(
        "features.execution.job_runner.run_deployment_cycle",
        run_cycle,
    )
    scheduled = "2026-05-28T14:00:00+00:00"
    await execute_execution_job(AsyncMock(), "execution_deployment_cycle", {"scheduled_at": scheduled})
    assert run_cycle.await_args.kwargs["as_of"] == datetime(
        2026, 5, 28, 14, 0, tzinfo=timezone.utc
    )
