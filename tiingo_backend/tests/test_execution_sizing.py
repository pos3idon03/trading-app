from features.execution.sizing import compute_buy_budget
from features.execution.signal_to_order import OrderIntent, signal_to_order_intent


def test_compute_buy_budget_uses_min_of_allocation_and_risk():
    budget = compute_buy_budget(
        buying_power=10_000,
        account_equity=10_000,
        allocation_pct=100,
        max_position_pct=5,
    )
    assert budget == 500


def test_signal_to_order_respects_max_position_pct():
    intent = signal_to_order_intent(
        "buy",
        symbol="AAPL",
        positions=[],
        buying_power=10_000,
        account_equity=10_000,
        allocation_pct=100,
        max_position_pct=5,
        last_price=100,
    )
    assert intent == OrderIntent(side="buy", qty=5.0, reason="buy_signal_flat")
