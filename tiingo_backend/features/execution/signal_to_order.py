from dataclasses import dataclass

from features.execution.order_qty import resolve_sell_qty
from features.execution.sizing import compute_buy_budget, round_buy_qty


@dataclass
class OrderIntent:
    side: str
    qty: float
    reason: str


def resolve_deployment_side(deployment_net_qty: float) -> str:
    if deployment_net_qty > 0:
        return "long"
    return "flat"


def signal_to_order_intent(
    signal: str,
    *,
    deployment_net_qty: float,
    buying_power: float,
    account_equity: float,
    allocation_pct: float,
    max_position_pct: float,
    last_price: float | None,
    asset_type: str = "stock",
    position_qty: float | None = None,
    qty_available: float | None = None,
) -> OrderIntent | None:
    side = resolve_deployment_side(deployment_net_qty)
    normalized = signal.lower()

    if normalized == "hold":
        return None
    if normalized == "buy" and side != "flat":
        return None
    if normalized == "sell" and side != "long":
        return None
    if last_price is None or last_price <= 0:
        return None

    if normalized == "buy":
        budget = compute_buy_budget(
            buying_power=buying_power,
            account_equity=account_equity,
            allocation_pct=allocation_pct,
            max_position_pct=max_position_pct,
        )
        qty = round_buy_qty(budget / last_price)
        if qty <= 0:
            return None
        return OrderIntent(side="buy", qty=qty, reason="buy_signal_flat")

    if normalized == "sell":
        qty = resolve_sell_qty(
            deployment_net_qty,
            asset_type=asset_type,
            position_qty=position_qty,
            qty_available=qty_available,
        )
        if qty <= 0:
            return None
        return OrderIntent(side="sell", qty=qty, reason="sell_signal_long")
    return None
