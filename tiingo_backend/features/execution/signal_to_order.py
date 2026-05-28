from dataclasses import dataclass

from features.execution.sizing import compute_buy_budget


@dataclass
class OrderIntent:
    side: str
    qty: float
    reason: str


def resolve_position_side(positions: list[dict], symbol: str) -> str:
    symbol = symbol.upper()
    for position in positions:
        if position.get("symbol", "").upper() != symbol:
            continue
        qty = float(position.get("qty") or 0)
        if qty > 0:
            return "long"
        if qty < 0:
            return "short"
    return "flat"


def signal_to_order_intent(
    signal: str,
    *,
    symbol: str,
    positions: list[dict],
    buying_power: float,
    account_equity: float,
    allocation_pct: float,
    max_position_pct: float,
    last_price: float | None,
) -> OrderIntent | None:
    side = resolve_position_side(positions, symbol)
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
        qty = budget / last_price
        if qty <= 0:
            return None
        return OrderIntent(side="buy", qty=qty, reason="buy_signal_flat")

    if normalized == "sell":
        position = next(
            (p for p in positions if p.get("symbol", "").upper() == symbol.upper()),
            None,
        )
        if not position:
            return None
        qty = abs(float(position.get("qty") or 0))
        if qty <= 0:
            return None
        return OrderIntent(side="sell", qty=qty, reason="sell_signal_long")
    return None
