from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import execution_order_dal
from features.execution import alpaca_client


def _parse_filled_at(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


async def sync_deployment_orders(session: AsyncSession, deployment_id: UUID) -> int:
    orders = await execution_order_dal.list_syncable_orders(session, deployment_id)
    updated = 0
    for order in orders:
        alpaca_id = order.get("alpaca_order_id")
        if not alpaca_id:
            continue
        remote = await alpaca_client.get_order(str(alpaca_id))
        filled_qty = remote.get("filled_qty")
        if filled_qty is None:
            filled_qty = remote.get("qty") if remote.get("status") == "filled" else None
        await execution_order_dal.update_order_status(
            session,
            order["id"],
            status=str(remote.get("status") or order["status"]),
            filled_avg_price=remote.get("filled_avg_price"),
            filled_at=_parse_filled_at(remote.get("filled_at")),
            filled_qty=float(filled_qty) if filled_qty is not None else None,
        )
        updated += 1
    return updated
