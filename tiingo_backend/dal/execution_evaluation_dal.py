from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.execution_evaluation import ExecutionEvaluation


async def create_evaluation(
    session: AsyncSession,
    *,
    deployment_id: UUID,
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
) -> dict:
    now = datetime.now(timezone.utc)
    row = ExecutionEvaluation(
        id=uuid4(),
        deployment_id=deployment_id,
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
        created_at=now,
    )
    session.add(row)
    await session.flush()
    return _to_dict(row)


async def list_evaluations(
    session: AsyncSession,
    *,
    deployment_id: UUID | None = None,
    symbol: str | None = None,
    limit: int = 50,
) -> list[dict]:
    from models.trading_deployment import TradingDeployment

    q = (
        select(ExecutionEvaluation, TradingDeployment)
        .join(TradingDeployment, ExecutionEvaluation.deployment_id == TradingDeployment.id)
        .order_by(ExecutionEvaluation.created_at.desc())
        .limit(limit)
    )
    if deployment_id:
        q = q.where(ExecutionEvaluation.deployment_id == deployment_id)
    if symbol:
        q = q.where(TradingDeployment.symbol == symbol.upper())

    rows = (await session.execute(q)).all()
    return [_to_dict(eval_row, deployment=dep_row) for eval_row, dep_row in rows]


def _to_dict(row: ExecutionEvaluation, *, deployment: object | None = None) -> dict:
    payload = {
        "id": row.id,
        "deployment_id": row.deployment_id,
        "bar_time": row.bar_time,
        "signal": row.signal,
        "probability": float(row.probability) if row.probability is not None else None,
        "buy_threshold": float(row.buy_threshold) if row.buy_threshold is not None else None,
        "sell_threshold": float(row.sell_threshold) if row.sell_threshold is not None else None,
        "position_side": row.position_side,
        "order_intent_side": row.order_intent_side,
        "order_qty": float(row.order_qty) if row.order_qty is not None else None,
        "outcome": row.outcome,
        "blocked_reason": row.blocked_reason,
        "order_id": row.order_id,
        "warnings": row.warnings or [],
        "created_at": row.created_at,
    }
    if deployment is not None:
        payload["symbol"] = deployment.symbol
        payload["model_id"] = deployment.model_id
    return payload
