from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dal import execution_order_dal, execution_settings_dal, instrument_dal
from features.execution import alpaca_client
from features.execution.alpaca_symbols import execution_asset_type
from features.execution.order_sync import sync_deployment_orders


async def close_deployment_position(session: AsyncSession, deployment: dict) -> dict:
    deployment_id = deployment["id"]
    await sync_deployment_orders(session, deployment_id)
    net_qty = await execution_order_dal.sum_filled_qty_by_deployment(session, deployment_id)
    if net_qty <= 0:
        return {"closed": False, "qty": 0.0, "order_id": None}

    if await execution_order_dal.has_open_order(session, deployment_id):
        raise ValueError("Open order pending for this deployment")

    instrument = await instrument_dal.get_by_symbol(session, deployment["symbol"])
    asset_type = execution_asset_type((instrument or {}).get("asset_type"))
    bar_time = datetime.now(timezone.utc)
    alpaca_order = await alpaca_client.submit_market_order(
        deployment["symbol"],
        net_qty,
        "sell",
        asset_type=asset_type,
    )
    await execution_settings_dal.record_order_submission(session)
    order_row = await execution_order_dal.create_order(
        session,
        deployment_id=deployment_id,
        alpaca_order_id=alpaca_order.get("id"),
        symbol=deployment["symbol"],
        side="sell",
        qty=net_qty,
        order_type="market",
        status=alpaca_order.get("status") or "pending",
        signal="manual_close",
        bar_time=bar_time,
    )
    return {"closed": True, "qty": net_qty, "order_id": order_row["id"]}
