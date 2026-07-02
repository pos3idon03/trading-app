from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from features.execution.deployment_reconciliation import (
    build_deployment_readiness,
    find_missed_slots,
    reconcile_missed_updates,
)
from features.execution.deployment_timeframes import (
    bar_time_for_evaluation_slot,
    expected_boundaries,
    floor_to_cron_slot,
)
from features.execution.job_runner import parse_scheduled_at


def test_floor_to_cron_slot():
    dt = datetime(2026, 5, 28, 14, 22, 45, tzinfo=timezone.utc)
    assert floor_to_cron_slot(dt) == datetime(2026, 5, 28, 14, 20, tzinfo=timezone.utc)


def test_bar_time_for_hourly_slot():
    slot = datetime(2026, 5, 28, 15, 0, tzinfo=timezone.utc)
    assert bar_time_for_evaluation_slot(slot, "1h") == datetime(
        2026, 5, 28, 14, 0, tzinfo=timezone.utc
    )


def test_expected_boundaries_hourly_during_session():
    start = datetime(2026, 5, 28, 13, 0, tzinfo=timezone.utc)
    end = datetime(2026, 5, 28, 16, 0, tzinfo=timezone.utc)
    boundaries = expected_boundaries("1h", start, end)
    assert boundaries == [
        datetime(2026, 5, 28, 14, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 28, 15, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 28, 16, 0, tzinfo=timezone.utc),
    ]


def test_find_missed_slots_for_stale_hourly_deployment():
    deployment = {
        "status": "active",
        "timeframe": "1h",
        "created_at": datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc),
        "last_evaluated_bar_time": datetime(2026, 5, 27, 19, 0, tzinfo=timezone.utc),
    }
    as_of = datetime(2026, 5, 28, 15, 20, tzinfo=timezone.utc)
    missed = find_missed_slots(deployment, as_of, grace_minutes=10)
    assert datetime(2026, 5, 28, 14, 0, tzinfo=timezone.utc) in missed
    assert datetime(2026, 5, 28, 15, 0, tzinfo=timezone.utc) in missed


def test_find_missed_slots_respects_grace_period():
    deployment = {
        "status": "active",
        "timeframe": "1h",
        "created_at": datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc),
        "last_evaluated_bar_time": datetime(2026, 5, 28, 13, 0, tzinfo=timezone.utc),
    }
    as_of = datetime(2026, 5, 28, 15, 5, tzinfo=timezone.utc)
    missed = find_missed_slots(deployment, as_of, grace_minutes=10)
    assert datetime(2026, 5, 28, 15, 0, tzinfo=timezone.utc) not in missed


def test_parse_scheduled_at():
    parsed = parse_scheduled_at({"scheduled_at": "2026-05-28T14:00:00+00:00"})
    assert parsed == datetime(2026, 5, 28, 14, 0, tzinfo=timezone.utc)
    assert parse_scheduled_at({}) is None


@pytest.mark.asyncio
async def test_build_deployment_readiness_marks_stale(monkeypatch):
    deployment = {
        "status": "active",
        "symbol": "IBM",
        "timeframe": "1h",
        "created_at": datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc),
        "last_evaluated_bar_time": datetime(2026, 5, 27, 19, 0, tzinfo=timezone.utc),
    }
    monkeypatch.setattr(
        "features.execution.deployment_reconciliation.check_ohlcv_freshness",
        AsyncMock(return_value=datetime(2026, 5, 27, 19, 0, tzinfo=timezone.utc)),
    )
    as_of = datetime(2026, 5, 28, 15, 20, tzinfo=timezone.utc)
    readiness = await build_deployment_readiness(AsyncMock(), deployment, as_of)
    assert readiness["update_status"] == "stale"
    assert readiness["missed_slot_count"] > 0


@pytest.mark.asyncio
async def test_build_deployment_readiness_tracks_ohlcv_for_error(monkeypatch):
    deployment = {
        "status": "error",
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "created_at": datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc),
        "last_evaluated_bar_time": datetime(2026, 5, 28, 17, 0, tzinfo=timezone.utc),
    }
    monkeypatch.setattr(
        "features.execution.deployment_reconciliation.check_ohlcv_freshness",
        AsyncMock(return_value=datetime(2026, 5, 28, 17, 0, tzinfo=timezone.utc)),
    )
    as_of = datetime(2026, 5, 28, 19, 20, tzinfo=timezone.utc)
    readiness = await build_deployment_readiness(
        AsyncMock(),
        deployment,
        as_of,
        asset_type="crypto",
    )
    assert readiness["update_status"] == "stale"
    assert readiness["missed_slot_count"] == 0
    assert readiness["ohlcv_latest_bar_time"] is not None


@pytest.mark.asyncio
async def test_reconcile_missed_updates_runs_catch_up(monkeypatch):
    deployment_id = uuid4()
    deployment = {
        "id": deployment_id,
        "status": "active",
        "symbol": "IBM",
        "timeframe": "1h",
        "created_at": datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc),
        "last_evaluated_bar_time": datetime(2026, 5, 27, 19, 0, tzinfo=timezone.utc),
    }
    run_cycle = AsyncMock(return_value={"skipped": False, "results": []})
    monkeypatch.setattr(
        "features.execution.deployment_reconciliation.trading_deployment_dal.list_active_deployments_with_instrument",
        AsyncMock(return_value=[{**deployment, "asset_type": "stock"}]),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_cycle.run_deployment_cycle",
        run_cycle,
    )
    as_of = datetime(2026, 5, 28, 15, 20, tzinfo=timezone.utc)
    result = await reconcile_missed_updates(AsyncMock(), as_of)
    assert result["catch_up_runs"] > 0
    run_cycle.assert_awaited()
    kwargs = run_cycle.await_args.kwargs
    assert kwargs["force_timeframes"] == {"1h"}
    assert kwargs["skip_reconciliation"] is True
