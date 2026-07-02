from features.execution.sizing import compute_buy_budget, round_buy_qty
from features.execution.signal_to_order import OrderIntent, signal_to_order_intent


def test_compute_buy_budget_uses_min_of_allocation_and_risk():
    budget = compute_buy_budget(
        buying_power=10_000,
        account_equity=10_000,
        allocation_pct=100,
        max_position_pct=5,
    )
    assert budget == 500


def test_round_buy_qty_rounds_to_two_decimals():
    assert round_buy_qty(0.0674187) == 0.07
    assert round_buy_qty(12.91494) == 12.91


def test_signal_to_order_respects_max_position_pct():
    intent = signal_to_order_intent(
        "buy",
        deployment_net_qty=0,
        buying_power=10_000,
        account_equity=10_000,
        allocation_pct=100,
        max_position_pct=5,
        last_price=100,
    )
    assert intent == OrderIntent(side="buy", qty=5.0, reason="buy_signal_flat")


def test_signal_to_order_buy_rounds_crypto_qty_to_two_decimals():
    intent = signal_to_order_intent(
        "buy",
        deployment_net_qty=0,
        buying_power=100_000,
        account_equity=100_000,
        allocation_pct=5,
        max_position_pct=100,
        last_price=74_112.9,
    )
    assert intent == OrderIntent(side="buy", qty=0.07, reason="buy_signal_flat")


def test_signal_to_order_buy_skips_when_rounded_qty_is_zero():
    intent = signal_to_order_intent(
        "buy",
        deployment_net_qty=0,
        buying_power=30,
        account_equity=30,
        allocation_pct=100,
        max_position_pct=100,
        last_price=10_000,
    )
    assert intent is None
