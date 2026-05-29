import pytest

from features.execution.risk_checker import (
    check_daily_loss,
    check_deployment_open_order,
    check_exposure,
    check_kill_switch,
    check_rate_limit,
)
from features.execution.signal_to_order import OrderIntent, resolve_deployment_side, signal_to_order_intent


def test_resolve_deployment_side_flat():
    assert resolve_deployment_side(0) == "flat"


def test_resolve_deployment_side_long():
    assert resolve_deployment_side(10) == "long"


def test_signal_to_order_intent_buy_when_deployment_flat():
    intent = signal_to_order_intent(
        "buy",
        deployment_net_qty=0,
        buying_power=10_000,
        account_equity=10_000,
        allocation_pct=100,
        max_position_pct=100,
        last_price=100,
    )
    assert intent == OrderIntent(side="buy", qty=100.0, reason="buy_signal_flat")


def test_signal_to_order_intent_buy_allowed_despite_external_position():
    intent = signal_to_order_intent(
        "buy",
        deployment_net_qty=0,
        buying_power=10_000,
        account_equity=10_000,
        allocation_pct=100,
        max_position_pct=100,
        last_price=100,
    )
    assert intent is not None
    assert intent.side == "buy"


def test_signal_to_order_intent_buy_blocked_when_deployment_long():
    intent = signal_to_order_intent(
        "buy",
        deployment_net_qty=5,
        buying_power=10_000,
        account_equity=10_000,
        allocation_pct=100,
        max_position_pct=100,
        last_price=100,
    )
    assert intent is None


def test_signal_to_order_intent_sell_uses_deployment_qty():
    intent = signal_to_order_intent(
        "sell",
        deployment_net_qty=2.5,
        buying_power=10_000,
        account_equity=10_000,
        allocation_pct=100,
        max_position_pct=100,
        last_price=100,
    )
    assert intent == OrderIntent(side="sell", qty=2.5, reason="sell_signal_long")


def test_signal_to_order_intent_hold_returns_none():
    assert (
        signal_to_order_intent(
            "hold",
            deployment_net_qty=0,
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


def test_check_deployment_open_order_blocks_when_open():
    result = check_deployment_open_order(True)
    assert not result.allowed


def test_check_exposure_uses_deployment_exposure_only():
    intent = OrderIntent(side="buy", qty=10, reason="buy_signal_flat")
    result = check_exposure(
        intent,
        account_equity=10_000,
        deployment_exposure=70_000,
        last_price=100,
        max_exposure_pct=80,
    )
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
