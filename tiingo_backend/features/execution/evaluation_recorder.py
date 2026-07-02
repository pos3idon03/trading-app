from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import execution_evaluation_dal, ml_model_dal, trading_deployment_dal
from features.execution.broadcaster import publish_activity_event


def _thresholds(hyperparams: dict) -> tuple[float | None, float | None]:
    label_mode = str(hyperparams.get("label_mode") or "binary")
    if label_mode == "meta_label":
        gate = hyperparams.get("meta_gate_threshold")
        return (
            float(gate) if gate is not None else None,
            None,
        )
    buy = hyperparams.get("buy_threshold")
    sell = hyperparams.get("sell_threshold")
    return (
        float(buy) if buy is not None else None,
        float(sell) if sell is not None else None,
    )


def build_activity_payload(
    *,
    deployment: dict,
    model: dict | None,
    evaluation: dict,
    symbol: str,
) -> dict[str, Any]:
    return {
        "id": str(evaluation["id"]),
        "deployment_id": str(deployment["id"]),
        "symbol": symbol,
        "model_id": str(deployment["model_id"]),
        "model_name": model.get("name") if model else None,
        "model_type": model.get("model_type") if model else None,
        "bar_time": evaluation["bar_time"].isoformat() if isinstance(evaluation["bar_time"], datetime) else evaluation["bar_time"],
        "signal": evaluation["signal"],
        "probability": evaluation.get("probability"),
        "buy_threshold": evaluation.get("buy_threshold"),
        "sell_threshold": evaluation.get("sell_threshold"),
        "position_side": evaluation.get("position_side"),
        "order_intent_side": evaluation.get("order_intent_side"),
        "order_qty": evaluation.get("order_qty"),
        "outcome": evaluation["outcome"],
        "blocked_reason": evaluation.get("blocked_reason"),
        "order_id": str(evaluation["order_id"]) if evaluation.get("order_id") else None,
        "warnings": evaluation.get("warnings") or [],
        "explainability": evaluation.get("explainability") or {},
        "created_at": evaluation["created_at"].isoformat() if isinstance(evaluation["created_at"], datetime) else evaluation["created_at"],
    }


async def record_evaluation(
    session: AsyncSession,
    *,
    deployment: dict,
    bar_time: datetime,
    signal: str,
    probability: float | None,
    buy_threshold: float | None,
    sell_threshold: float | None,
    position_side: str | None,
    order_intent_side: str | None,
    order_qty: float | None,
    outcome: str,
    blocked_reason: str | None,
    order_id: UUID | None,
    warnings: list[str],
    explainability: dict | None = None,
    skip_last_evaluated_at: bool = False,
) -> dict:
    explainability_payload = explainability or {}
    evaluation = await execution_evaluation_dal.create_evaluation(
        session,
        deployment_id=deployment["id"],
        bar_time=bar_time,
        signal=signal,
        probability=probability,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
        position_side=position_side,
        order_intent_side=order_intent_side,
        order_qty=order_qty,
        outcome=outcome,
        blocked_reason=blocked_reason,
        order_id=order_id,
        warnings=warnings,
        explainability=explainability_payload,
    )
    status_update = None
    clear_last_error = False
    last_error_update = None
    if outcome == "error":
        last_error_update = blocked_reason
    elif outcome == "order_submitted":
        clear_last_error = True
        if deployment.get("status") == "error":
            status_update = "active"
    else:
        clear_last_error = True

    await trading_deployment_dal.update_deployment_evaluation(
        session,
        deployment["id"],
        last_evaluated_bar_time=bar_time,
        last_evaluated_at=evaluation["created_at"],
        last_signal=signal,
        last_error=last_error_update,
        last_blocked_reason=blocked_reason,
        last_probability=probability,
        last_explainability=explainability_payload,
        last_outcome=outcome,
        status=status_update,
        clear_last_error=clear_last_error,
        skip_last_evaluated_at=skip_last_evaluated_at,
    )
    model = await ml_model_dal.get_model(session, deployment["model_id"])
    payload = build_activity_payload(
        deployment=deployment,
        model=model,
        evaluation=evaluation,
        symbol=deployment["symbol"],
    )
    await publish_activity_event(payload)
    evaluation["activity"] = payload
    return evaluation
