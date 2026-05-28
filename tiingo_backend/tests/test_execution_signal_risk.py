import pytest

from features.execution.risk_checker import (
    check_daily_loss,
    check_kill_switch,
    check_open_orders,
    check_rate_limit,
)
from features.execution.signal_to_order import OrderIntent, resolve_position_side, signal_to_order_intent


def test_resolve_position_side_flat():
    assert resolve_position_side([], "AAPL") == "flat"


def test_resolve_position_side_long():
    positions = [{"symbol": "AAPL", "qty": 10}]
    assert resolve_position_side(positions, "AAPL") == "long"


def test_signal_to_order_intent_buy_when_flat():
    intent = signal_to_order_intent(
        "buy",
        symbol="AAPL",
        positions=[],
        buying_power=10_000,
        account_equity=10_000,
        allocation_pct=100,
        max_position_pct=100,
        last_price=100,
    )
    assert intent == OrderIntent(side="buy", qty=100.0, reason="buy_signal_flat")


def test_signal_to_order_intent_sell_when_long():
    positions = [{"symbol": "AAPL", "qty": 5}]
    intent = signal_to_order_intent(
        "sell",
        symbol="AAPL",
        positions=positions,
        buying_power=10_000,
        account_equity=10_000,
        allocation_pct=100,
        max_position_pct=100,
        last_price=100,
    )
    assert intent == OrderIntent(side="sell", qty=5.0, reason="sell_signal_long")


def test_signal_to_order_intent_hold_returns_none():
    assert (
        signal_to_order_intent(
            "hold",
            symbol="AAPL",
            positions=[],
            buying_power=10_000,
            account_equity=10_000,
            allocation_pct=100,
            max_position_pct=100,
            last_price=100,
        )
        is None
    )


def test_check_kill_switch_blocks_when_enabled():
    result = check_kill_switch(True)
    assert not result.allowed


def test_check_rate_limit_blocks_when_exceeded():
    result = check_rate_limit(10, 10)
    assert not result.allowed


def test_check_open_orders_blocks_duplicate_symbol():
    result = check_open_orders([{"symbol": "AAPL"}], "AAPL")
    assert not result.allowed


def test_check_daily_loss_blocks_when_limit_hit():
    from datetime import date

    result = check_daily_loss(
        current_equity=9000,
        day_start_equity=10_000,
        day_start_date=date.today(),
        today=date.today(),
        limit_pct=5.0,
    )
    assert not result.allowed
