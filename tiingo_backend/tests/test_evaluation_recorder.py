from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from features.execution.evaluation_recorder import build_activity_payload, record_evaluation


def test_build_activity_payload_includes_explainability():
    deployment_id = uuid4()
    evaluation = {
        "id": uuid4(),
        "bar_time": datetime(2026, 5, 28, 15, tzinfo=timezone.utc),
        "signal": "buy",
        "probability": 0.72,
        "buy_threshold": 0.6,
        "sell_threshold": 0.4,
        "position_side": "flat",
        "order_intent_side": "buy",
        "order_qty": 1.0,
        "outcome": "order_submitted",
        "blocked_reason": None,
        "order_id": None,
        "warnings": [],
        "explainability": {
            "method": "shap_tree",
            "top_contributors": [
                {"feature": "ret_5", "value": 0.03, "contribution": 0.1},
            ],
            "warnings": [],
        },
        "created_at": datetime(2026, 5, 28, 15, 1, tzinfo=timezone.utc),
    }
    payload = build_activity_payload(
        deployment={"id": deployment_id, "model_id": uuid4()},
        model={"name": "AAPL model", "model_type": "ml_logistic"},
        evaluation=evaluation,
        symbol="AAPL",
    )
    assert payload["explainability"]["method"] == "shap_tree"
    assert payload["explainability"]["top_contributors"][0]["feature"] == "ret_5"


@pytest.mark.asyncio
async def test_record_evaluation_persists_explainability(monkeypatch):
    deployment_id = uuid4()
    evaluation_id = uuid4()
    explainability = {
        "method": "shap_linear",
        "top_contributors": [],
        "warnings": [],
    }
    create_evaluation = AsyncMock(
        return_value={
            "id": evaluation_id,
            "bar_time": datetime(2026, 5, 28, 15, tzinfo=timezone.utc),
            "signal": "hold",
            "probability": 0.5,
            "buy_threshold": 0.6,
            "sell_threshold": 0.4,
            "position_side": "flat",
            "order_intent_side": None,
            "order_qty": None,
            "outcome": "hold",
            "blocked_reason": None,
            "order_id": None,
            "warnings": [],
            "explainability": explainability,
            "created_at": datetime(2026, 5, 28, 15, 1, tzinfo=timezone.utc),
        }
    )
    update_evaluation = AsyncMock()
    publish = AsyncMock()
    get_model = AsyncMock(return_value={"name": "model", "model_type": "ml_logistic"})

    monkeypatch.setattr(
        "features.execution.evaluation_recorder.execution_evaluation_dal.create_evaluation",
        create_evaluation,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.trading_deployment_dal.update_deployment_evaluation",
        update_evaluation,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.ml_model_dal.get_model",
        get_model,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.publish_activity_event",
        publish,
    )

    await record_evaluation(
        AsyncMock(),
        deployment={"id": deployment_id, "model_id": uuid4(), "symbol": "AAPL"},
        bar_time=datetime(2026, 5, 28, 15, tzinfo=timezone.utc),
        signal="hold",
        probability=0.5,
        buy_threshold=0.6,
        sell_threshold=0.4,
        position_side="flat",
        order_intent_side=None,
        order_qty=None,
        outcome="hold",
        blocked_reason=None,
        order_id=None,
        warnings=[],
        explainability=explainability,
    )

    create_evaluation.assert_awaited_once()
    assert create_evaluation.await_args.kwargs["explainability"] == explainability
    update_evaluation.assert_awaited_once()
    assert update_evaluation.await_args.kwargs["last_explainability"] == explainability
    assert update_evaluation.await_args.kwargs["clear_last_error"] is True
    assert "last_evaluated_at" in update_evaluation.await_args.kwargs
    publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_evaluation_can_skip_last_evaluated_at(monkeypatch):
    deployment_id = uuid4()
    update_evaluation = AsyncMock()
    created_at = datetime(2026, 5, 28, 15, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.execution_evaluation_dal.create_evaluation",
        AsyncMock(
            return_value={
                "id": uuid4(),
                "bar_time": datetime(2026, 5, 28, 15, tzinfo=timezone.utc),
                "signal": "buy",
                "probability": 0.5,
                "buy_threshold": 0.6,
                "sell_threshold": 0.4,
                "position_side": "flat",
                "order_intent_side": None,
                "order_qty": None,
                "outcome": "blocked",
                "blocked_reason": "Market data not ready",
                "order_id": None,
                "warnings": [],
                "explainability": {},
                "created_at": created_at,
            }
        ),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.trading_deployment_dal.update_deployment_evaluation",
        update_evaluation,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.ml_model_dal.get_model",
        AsyncMock(return_value={"name": "AAPL", "model_type": "ml_logistic"}),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.publish_activity_event",
        AsyncMock(),
    )

    await record_evaluation(
        AsyncMock(),
        deployment={"id": deployment_id, "model_id": uuid4(), "symbol": "AAPL"},
        bar_time=datetime(2026, 5, 28, 15, tzinfo=timezone.utc),
        signal="buy",
        probability=0.5,
        buy_threshold=0.6,
        sell_threshold=0.4,
        position_side="flat",
        order_intent_side=None,
        order_qty=None,
        outcome="blocked",
        blocked_reason="Market data not ready",
        order_id=None,
        warnings=[],
        skip_last_evaluated_at=True,
    )

    assert update_evaluation.await_args.kwargs["skip_last_evaluated_at"] is True


@pytest.mark.asyncio
async def test_record_evaluation_preserves_error_on_order_failure(monkeypatch):
    deployment_id = uuid4()
    update_evaluation = AsyncMock()
    created_at = datetime(2026, 5, 28, 15, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.execution_evaluation_dal.create_evaluation",
        AsyncMock(
            return_value={
                "id": uuid4(),
                "bar_time": datetime(2026, 5, 28, 15, tzinfo=timezone.utc),
                "signal": "sell",
                "probability": 0.2,
                "buy_threshold": 0.6,
                "sell_threshold": 0.4,
                "position_side": "long",
                "order_intent_side": "sell",
                "order_qty": 0.5,
                "outcome": "error",
                "blocked_reason": "Alpaca API error 403: forbidden",
                "order_id": None,
                "warnings": [],
                "explainability": {},
                "created_at": created_at,
            }
        ),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.trading_deployment_dal.update_deployment_evaluation",
        update_evaluation,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.ml_model_dal.get_model",
        AsyncMock(return_value={"name": "BTC model", "model_type": "ml_xgboost"}),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.publish_activity_event",
        AsyncMock(),
    )

    await record_evaluation(
        AsyncMock(),
        deployment={
            "id": deployment_id,
            "model_id": uuid4(),
            "symbol": "BTC-USD",
            "status": "error",
        },
        bar_time=datetime(2026, 5, 28, 15, tzinfo=timezone.utc),
        signal="sell",
        probability=0.2,
        buy_threshold=0.6,
        sell_threshold=0.4,
        position_side="long",
        order_intent_side="sell",
        order_qty=0.5,
        outcome="error",
        blocked_reason="Alpaca API error 403: forbidden",
        order_id=None,
        warnings=[],
    )

    kwargs = update_evaluation.await_args.kwargs
    assert kwargs["last_error"] == "Alpaca API error 403: forbidden"
    assert kwargs.get("clear_last_error") is not True
    assert kwargs.get("status") is None
    assert kwargs["last_evaluated_at"] == created_at


@pytest.mark.asyncio
async def test_record_evaluation_clears_error_and_reactivates(monkeypatch):
    deployment_id = uuid4()
    update_evaluation = AsyncMock()
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.execution_evaluation_dal.create_evaluation",
        AsyncMock(
            return_value={
                "id": uuid4(),
                "bar_time": datetime(2026, 5, 28, 15, tzinfo=timezone.utc),
                "signal": "hold",
                "probability": 0.5,
                "buy_threshold": 0.6,
                "sell_threshold": 0.4,
                "position_side": "flat",
                "order_intent_side": None,
                "order_qty": None,
                "outcome": "order_submitted",
                "blocked_reason": None,
                "order_id": uuid4(),
                "warnings": [],
                "explainability": {},
                "created_at": datetime(2026, 5, 28, 15, 1, tzinfo=timezone.utc),
            }
        ),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.trading_deployment_dal.update_deployment_evaluation",
        update_evaluation,
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.ml_model_dal.get_model",
        AsyncMock(return_value={"name": "MSFT model", "model_type": "ml_logistic"}),
    )
    monkeypatch.setattr(
        "features.execution.evaluation_recorder.publish_activity_event",
        AsyncMock(),
    )

    await record_evaluation(
        AsyncMock(),
        deployment={
            "id": deployment_id,
            "model_id": uuid4(),
            "symbol": "MSFT",
            "status": "error",
        },
        bar_time=datetime(2026, 5, 28, 15, tzinfo=timezone.utc),
        signal="buy",
        probability=0.5,
        buy_threshold=0.6,
        sell_threshold=0.4,
        position_side="flat",
        order_intent_side="buy",
        order_qty=1.0,
        outcome="order_submitted",
        blocked_reason=None,
        order_id=uuid4(),
        warnings=[],
    )

    kwargs = update_evaluation.await_args.kwargs
    assert kwargs["clear_last_error"] is True
    assert kwargs["status"] == "active"
