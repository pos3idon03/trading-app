from features.execution.deployment_position import (
    compute_net_qty,
    effective_filled_qty,
    is_open_order_status,
    resolve_deployment_side,
)


def test_effective_filled_qty_uses_filled_qty_when_present():
    order = {"status": "filled", "qty": 10, "filled_qty": 8}
    assert effective_filled_qty(order) == 8


def test_effective_filled_qty_ignores_pending():
    order = {"status": "accepted", "qty": 10}
    assert effective_filled_qty(order) == 0


def test_compute_net_qty_buy_minus_sell():
    orders = [
        {"status": "filled", "side": "buy", "qty": 10},
        {"status": "filled", "side": "sell", "qty": 3},
    ]
    assert compute_net_qty(orders) == 7


def test_compute_net_qty_never_negative():
    orders = [{"status": "filled", "side": "sell", "qty": 5}]
    assert compute_net_qty(orders) == 0


def test_resolve_deployment_side():
    assert resolve_deployment_side(0) == "flat"
    assert resolve_deployment_side(1.5) == "long"


def test_is_open_order_status():
    assert is_open_order_status("accepted")
    assert not is_open_order_status("filled")
    assert not is_open_order_status("canceled")
