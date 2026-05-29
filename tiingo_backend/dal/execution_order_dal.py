from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from features.execution.deployment_position import compute_net_qty, effective_filled_qty, is_open_order_status
from models.execution_order import ExecutionOrder


async def create_order(
    session: AsyncSession,
    *,
    deployment_id: UUID,
    alpaca_order_id: str | None,
    symbol: str,
    side: str,
    qty: float,
    order_type: str,
    status: str,
    signal: str,
    bar_time: datetime,
    error_message: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    row = ExecutionOrder(
        id=uuid4(),
        deployment_id=deployment_id,
        alpaca_order_id=alpaca_order_id,
        symbol=symbol.upper(),
        side=side,
        qty=qty,
        order_type=order_type,
        status=status,
        signal=signal,
        bar_time=bar_time,
        submitted_at=now,
        error_message=error_message,
    )
    session.add(row)
    await session.flush()
    return _to_dict(row)


async def get_order(session: AsyncSession, order_id: UUID) -> dict | None:
    q = select(ExecutionOrder).where(ExecutionOrder.id == order_id)
    row = (await session.execute(q)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def get_order_by_alpaca_id(session: AsyncSession, alpaca_order_id: str) -> dict | None:
    q = select(ExecutionOrder).where(ExecutionOrder.alpaca_order_id == alpaca_order_id)
    row = (await session.execute(q)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def list_orders(
    session: AsyncSession,
    *,
    deployment_id: UUID | None = None,
    symbol: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    q = select(ExecutionOrder).order_by(ExecutionOrder.submitted_at.desc()).limit(limit)
    if deployment_id:
        q = q.where(ExecutionOrder.deployment_id == deployment_id)
    if symbol:
        q = q.where(ExecutionOrder.symbol == symbol.upper())
    if status:
        q = q.where(ExecutionOrder.status == status)
    rows = (await session.execute(q)).scalars().all()
    return [_to_dict(row) for row in rows]


async def list_filled_orders_for_deployments(
    session: AsyncSession,
    deployment_ids: list[UUID],
) -> list[dict]:
    if not deployment_ids:
        return []
    q = (
        select(ExecutionOrder)
        .where(ExecutionOrder.deployment_id.in_(deployment_ids))
        .order_by(ExecutionOrder.submitted_at.asc())
    )
    rows = (await session.execute(q)).scalars().all()
    return [_to_dict(row) for row in rows if effective_filled_qty(_to_dict(row)) > 0]


async def list_orders_for_deployment(
    session: AsyncSession,
    deployment_id: UUID,
    *,
    limit: int | None = None,
) -> list[dict]:
    q = (
        select(ExecutionOrder)
        .where(ExecutionOrder.deployment_id == deployment_id)
        .order_by(ExecutionOrder.submitted_at.desc())
    )
    if limit is not None:
        q = q.limit(limit)
    rows = (await session.execute(q)).scalars().all()
    return [_to_dict(row) for row in rows]


async def sum_filled_qty_by_deployment(session: AsyncSession, deployment_id: UUID) -> float:
    orders = await list_orders_for_deployment(session, deployment_id)
    return compute_net_qty(orders)


async def has_open_order(session: AsyncSession, deployment_id: UUID) -> bool:
    orders = await list_orders_for_deployment(session, deployment_id, limit=50)
    return any(is_open_order_status(order["status"]) for order in orders)


async def count_orders_by_deployment(session: AsyncSession, deployment_id: UUID) -> int:
    q = select(func.count()).select_from(ExecutionOrder).where(
        ExecutionOrder.deployment_id == deployment_id,
    )
    result = await session.execute(q)
    return int(result.scalar_one() or 0)


async def count_open_orders_by_deployment(session: AsyncSession, deployment_id: UUID) -> int:
    orders = await list_orders_for_deployment(session, deployment_id)
    return sum(1 for order in orders if is_open_order_status(order.get("status")))


async def list_syncable_orders(session: AsyncSession, deployment_id: UUID) -> list[dict]:
    orders = await list_orders_for_deployment(session, deployment_id, limit=100)
    return [
        order
        for order in orders
        if order.get("alpaca_order_id") and is_open_order_status(order.get("status"))
    ]


async def update_order_status(
    session: AsyncSession,
    order_id: UUID,
    *,
    status: str,
    filled_avg_price: float | None = None,
    filled_at: datetime | None = None,
    filled_qty: float | None = None,
    error_message: str | None = None,
) -> dict | None:
    values: dict = {"status": status}
    if filled_avg_price is not None:
        values["filled_avg_price"] = filled_avg_price
    if filled_at is not None:
        values["filled_at"] = filled_at
    if filled_qty is not None:
        values["filled_qty"] = filled_qty
    if error_message is not None:
        values["error_message"] = error_message
    await session.execute(
        update(ExecutionOrder).where(ExecutionOrder.id == order_id).values(**values),
    )
    await session.flush()
    return await get_order(session, order_id)


def _to_dict(row: ExecutionOrder) -> dict:
    return {
        "id": row.id,
        "deployment_id": row.deployment_id,
        "alpaca_order_id": row.alpaca_order_id,
        "symbol": row.symbol,
        "side": row.side,
        "qty": float(row.qty),
        "filled_qty": float(row.filled_qty) if row.filled_qty is not None else None,
        "order_type": row.order_type,
        "status": row.status,
        "signal": row.signal,
        "bar_time": row.bar_time,
        "filled_avg_price": float(row.filled_avg_price) if row.filled_avg_price else None,
        "submitted_at": row.submitted_at,
        "filled_at": row.filled_at,
        "error_message": row.error_message,
    }
