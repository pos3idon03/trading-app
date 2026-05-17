"""Sync local order records with Alpaca after submit and on read."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from features.execution.broker_client import OrderResult, fetch_order_by_id, is_terminal_order_status
from utils.logging import get_logger

logger = get_logger(__name__)

_POLL_DELAYS_SEC = (0.2, 0.3, 0.5, 0.5, 1.0, 1.0, 1.5)


def wait_for_order_terminal(
    alpaca_order_id: str,
    initial: OrderResult,
    max_wait_sec: float = 5.0,
) -> OrderResult:
    """Poll Alpaca until the order reaches a terminal status or timeout."""
    if not alpaca_order_id:
        return initial

    latest = initial
    if is_terminal_order_status(latest.status):
        return latest

    deadline = time.monotonic() + max_wait_sec
    for delay in _POLL_DELAYS_SEC:
        if time.monotonic() >= deadline:
            break
        time.sleep(min(delay, max(0, deadline - time.monotonic())))
        fetched = fetch_order_by_id(alpaca_order_id)
        if fetched is None:
            continue
        latest = fetched
        if is_terminal_order_status(latest.status):
            logger.info(
                "order_reached_terminal",
                alpaca_order_id=alpaca_order_id,
                status=latest.status,
            )
            return latest

    return latest


def parse_filled_at(order_result: OrderResult) -> datetime | None:
    """Use filled_at from broker when present; otherwise now for filled orders."""
    if order_result.filled_at is not None:
        return order_result.filled_at
    if is_terminal_order_status(order_result.status) and order_result.status.lower() == "filled":
        return datetime.now(timezone.utc)
    return None


async def refresh_open_orders_from_alpaca(session, orders: list) -> None:
    """Update non-terminal local orders from Alpaca (lazy heal on read)."""
    from dal.execution_dal import update_order_status

    for order in orders:
        if not order.alpaca_order_id or is_terminal_order_status(order.status):
            continue
        fetched = fetch_order_by_id(order.alpaca_order_id)
        if fetched is None:
            continue
        if (
            fetched.status == order.status
            and fetched.filled_price == order.filled_price
            and fetched.filled_qty == order.filled_qty
        ):
            continue
        await update_order_status(
            session,
            order.id,
            status=fetched.status,
            filled_price=fetched.filled_price,
            filled_qty=fetched.filled_qty,
            filled_at=parse_filled_at(fetched),
        )
        order.status = fetched.status
        order.filled_price = fetched.filled_price
        order.filled_qty = fetched.filled_qty
        order.filled_at = parse_filled_at(fetched)
