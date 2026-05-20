"""DAL for orders, risk events, and portfolio snapshots."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import desc, select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from models.execution import Order, PortfolioSnapshot, RiskEvent
from utils.logging import get_logger

logger = get_logger(__name__)

OPEN_ORDER_STATUSES = frozenset({
    "pending",
    "pending_new",
    "accepted",
    "new",
    "partially_filled",
})


async def has_open_order_for_symbol(
    session: AsyncSession,
    symbol: str,
    side: str | None = None,
) -> bool:
    """True if a non-terminal order exists for symbol (optionally matching side)."""
    stmt = select(Order.id).where(
        Order.symbol == symbol,
        Order.status.in_(OPEN_ORDER_STATUSES),
    )
    if side is not None:
        stmt = stmt.where(Order.side == side.lower())
    result = await session.execute(stmt.limit(1))
    return result.scalar_one_or_none() is not None


async def create_order(
    session: AsyncSession,
    symbol: str,
    side: str,
    qty: float,
    order_type: str = "market",
    asset_id: int | None = None,
    limit_price: float | None = None,
    stop_price: float | None = None,
    signal_id: int | None = None,
) -> int:
    record = Order(
        asset_id=asset_id,
        symbol=symbol,
        side=side,
        qty=qty,
        order_type=order_type,
        limit_price=limit_price,
        stop_price=stop_price,
        signal_id=signal_id,
        status="pending",
    )
    session.add(record)
    await session.flush()
    return record.id


async def update_order_status(
    session: AsyncSession,
    order_id: int,
    status: str,
    alpaca_order_id: str | None = None,
    filled_price: float | None = None,
    filled_qty: float | None = None,
    filled_at: datetime | None = None,
    error_message: str | None = None,
) -> None:
    order = await session.get(Order, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")
    order.status = status
    if alpaca_order_id:
        order.alpaca_order_id = alpaca_order_id
    if filled_price is not None:
        order.filled_price = filled_price
    if filled_qty is not None:
        order.filled_qty = filled_qty
    if filled_at is not None:
        order.filled_at = filled_at
    if error_message:
        order.error_message = error_message


async def get_order(session: AsyncSession, order_id: int) -> Optional[Order]:
    return await session.get(Order, order_id)


async def get_order_history(
    session: AsyncSession, symbol: str | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[Order], int]:
    base = select(Order)
    count_base = select(sa_func.count(Order.id))

    if symbol:
        base = base.where(Order.symbol == symbol)
        count_base = count_base.where(Order.symbol == symbol)

    count_result = await session.execute(count_base)
    total = count_result.scalar() or 0

    stmt = base.order_by(desc(Order.created_at)).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all()), total


async def count_recent_orders(session: AsyncSession, minutes: int = 1) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    stmt = select(sa_func.count(Order.id)).where(Order.created_at >= cutoff)
    result = await session.execute(stmt)
    return result.scalar() or 0


async def create_risk_event(
    session: AsyncSession,
    event_type: str,
    description: str,
    severity: str = "warning",
    symbol: str | None = None,
    asset_id: int | None = None,
    details: dict | None = None,
) -> int:
    record = RiskEvent(
        asset_id=asset_id,
        event_type=event_type,
        severity=severity,
        symbol=symbol,
        description=description,
        details=details,
    )
    session.add(record)
    await session.flush()
    return record.id


async def get_risk_events(
    session: AsyncSession, limit: int = 50, offset: int = 0,
) -> tuple[list[RiskEvent], int]:
    count_result = await session.execute(select(sa_func.count(RiskEvent.id)))
    total = count_result.scalar() or 0

    stmt = select(RiskEvent).order_by(desc(RiskEvent.created_at)).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all()), total


async def create_portfolio_snapshot(
    session: AsyncSession,
    equity: float,
    cash: float,
    buying_power: float,
    daily_pnl: float | None = None,
    daily_pnl_pct: float | None = None,
    total_positions: int = 0,
    positions: dict | None = None,
) -> int:
    record = PortfolioSnapshot(
        equity=equity,
        cash=cash,
        buying_power=buying_power,
        daily_pnl=daily_pnl,
        daily_pnl_pct=daily_pnl_pct,
        total_positions=total_positions,
        positions=positions,
    )
    session.add(record)
    await session.flush()
    return record.id


async def get_latest_portfolio_snapshot(
    session: AsyncSession,
) -> Optional[PortfolioSnapshot]:
    stmt = (
        select(PortfolioSnapshot)
        .order_by(desc(PortfolioSnapshot.created_at))
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
