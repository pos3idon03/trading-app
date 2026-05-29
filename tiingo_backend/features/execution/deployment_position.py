POSITION_FILLED_STATUSES = frozenset({"filled", "partially_filled"})

TERMINAL_ORDER_STATUSES = frozenset({
    "filled",
    "canceled",
    "cancelled",
    "expired",
    "rejected",
    "failed",
    "done_for_day",
})


def effective_filled_qty(order: dict) -> float:
    status = (order.get("status") or "").lower()
    if status not in POSITION_FILLED_STATUSES:
        return 0.0
    filled_qty = order.get("filled_qty")
    if filled_qty is not None:
        return float(filled_qty)
    return float(order.get("qty") or 0)


def compute_net_qty(orders: list[dict]) -> float:
    net = 0.0
    for order in orders:
        qty = effective_filled_qty(order)
        if qty <= 0:
            continue
        side = (order.get("side") or "").lower()
        if side == "buy":
            net += qty
        elif side == "sell":
            net -= qty
    return max(net, 0.0)


def resolve_deployment_side(net_qty: float) -> str:
    if net_qty > 0:
        return "long"
    return "flat"


def is_open_order_status(status: str | None) -> bool:
    normalized = (status or "").lower()
    if not normalized:
        return True
    return normalized not in TERMINAL_ORDER_STATUSES
