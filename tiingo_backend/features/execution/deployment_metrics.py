from dataclasses import dataclass
from datetime import datetime

from features.execution.deployment_position import effective_filled_qty


@dataclass(frozen=True)
class StrategyPnl:
    realized_profit: float
    unrealized_profit: float
    round_trip_count: int
    position_qty: float
    avg_entry_price: float
    closed_cost_basis: float
    open_cost_basis: float

    @property
    def total_profit(self) -> float:
        return self.realized_profit + self.unrealized_profit

    @property
    def profit_pct(self) -> float | None:
        basis = self.closed_cost_basis + self.open_cost_basis
        if basis <= 0:
            return None
        return (self.total_profit / basis) * 100.0


def _order_sort_key(order: dict) -> datetime:
    filled_at = order.get("filled_at")
    submitted_at = order.get("submitted_at")
    if filled_at is not None:
        return filled_at
    if submitted_at is not None:
        return submitted_at
    return datetime.min


def filled_orders_chronological(orders: list[dict]) -> list[dict]:
    filled = [order for order in orders if effective_filled_qty(order) > 0]
    return sorted(filled, key=_order_sort_key)


def compute_round_trip_count(orders: list[dict]) -> int:
    net = 0.0
    round_trips = 0
    was_long = False
    for order in filled_orders_chronological(orders):
        qty = effective_filled_qty(order)
        side = (order.get("side") or "").lower()
        if side == "buy":
            net += qty
        elif side == "sell":
            net -= qty
        if net > 1e-8:
            was_long = True
        if net <= 1e-8 and was_long:
            round_trips += 1
            was_long = False
            net = max(net, 0.0)
    return round_trips


def compute_strategy_pnl(orders: list[dict], current_price: float) -> StrategyPnl:
    lots: list[list[float]] = []
    realized = 0.0
    closed_cost_basis = 0.0

    for order in filled_orders_chronological(orders):
        qty = effective_filled_qty(order)
        price = float(order.get("filled_avg_price") or 0)
        side = (order.get("side") or "").lower()
        if side == "buy":
            lots.append([qty, price])
            continue
        if side != "sell":
            continue

        remaining = qty
        while remaining > 1e-8 and lots:
            lot_qty, lot_price = lots[0]
            take = min(remaining, lot_qty)
            realized += take * (price - lot_price)
            closed_cost_basis += take * lot_price
            remaining -= take
            if lot_qty - take <= 1e-8:
                lots.pop(0)
            else:
                lots[0][0] = lot_qty - take

    position_qty = sum(lot[0] for lot in lots)
    open_cost_basis = sum(lot[0] * lot[1] for lot in lots)
    avg_entry = open_cost_basis / position_qty if position_qty > 1e-8 else 0.0
    unrealized = position_qty * (current_price - avg_entry) if position_qty > 1e-8 else 0.0

    return StrategyPnl(
        realized_profit=realized,
        unrealized_profit=unrealized,
        round_trip_count=compute_round_trip_count(orders),
        position_qty=position_qty,
        avg_entry_price=avg_entry,
        closed_cost_basis=closed_cost_basis,
        open_cost_basis=open_cost_basis,
    )
