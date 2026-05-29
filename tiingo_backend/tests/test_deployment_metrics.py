from datetime import datetime, timezone
from uuid import uuid4

from features.execution.deployment_metrics import (
    compute_round_trip_count,
    compute_strategy_pnl,
)


def _order(
    *,
    side: str,
    qty: float,
    price: float,
    submitted_at: datetime,
    status: str = "filled",
) -> dict:
    return {
        "id": uuid4(),
        "side": side,
        "qty": qty,
        "filled_qty": qty,
        "filled_avg_price": price,
        "status": status,
        "submitted_at": submitted_at,
        "filled_at": submitted_at,
    }


def test_round_trip_count_single_complete_cycle():
    t0 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    t1 = datetime(2026, 5, 2, tzinfo=timezone.utc)
    orders = [
        _order(side="buy", qty=10, price=100, submitted_at=t0),
        _order(side="sell", qty=10, price=110, submitted_at=t1),
    ]
    assert compute_round_trip_count(orders) == 1


def test_round_trip_count_partial_sells_count_one_trip():
    t0 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    t1 = datetime(2026, 5, 2, tzinfo=timezone.utc)
    t2 = datetime(2026, 5, 3, tzinfo=timezone.utc)
    orders = [
        _order(side="buy", qty=10, price=100, submitted_at=t0),
        _order(side="sell", qty=5, price=110, submitted_at=t1),
        _order(side="sell", qty=5, price=105, submitted_at=t2),
    ]
    assert compute_round_trip_count(orders) == 1


def test_strategy_pnl_realized_on_flat_position():
    t0 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    t1 = datetime(2026, 5, 2, tzinfo=timezone.utc)
    orders = [
        _order(side="buy", qty=10, price=100, submitted_at=t0),
        _order(side="sell", qty=10, price=110, submitted_at=t1),
    ]
    pnl = compute_strategy_pnl(orders, current_price=110)
    assert pnl.realized_profit == 100
    assert pnl.unrealized_profit == 0
    assert pnl.total_profit == 100
    assert pnl.profit_pct == 10.0


def test_strategy_pnl_unrealized_on_open_position():
    t0 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    orders = [_order(side="buy", qty=10, price=100, submitted_at=t0)]
    pnl = compute_strategy_pnl(orders, current_price=105)
    assert pnl.realized_profit == 0
    assert pnl.unrealized_profit == 50
    assert pnl.total_profit == 50
    assert pnl.profit_pct == 5.0
