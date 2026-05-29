from datetime import date

from features.execution.risk_checker import (
    RiskCheckResult,
    check_deployment_drawdown,
    check_stale_data,
    run_risk_checks,
)
from features.execution.signal_to_order import OrderIntent


def test_check_deployment_drawdown_blocks_when_exceeded():
    result = check_deployment_drawdown(
        strategy_profit_pct=2.0,
        peak_strategy_profit_pct=20.0,
        max_drawdown_pct=15.0,
    )
    assert result.allowed is False
    assert "drawdown" in (result.reason or "").lower()


def test_check_stale_data_blocks_when_missed_slots_exceeded():
    result = check_stale_data(
        {"update_status": "stale", "missed_slot_count": 3},
        enabled=True,
        max_missed_slots=2,
    )
    assert result.allowed is False
    assert "stale" in (result.reason or "").lower()


def test_run_risk_checks_includes_drawdown_and_stale(monkeypatch):
    monkeypatch.setattr(
        "features.execution.risk_checker.get_settings",
        lambda: type(
            "S",
            (),
            {
                "max_orders_per_minute": 10,
                "daily_loss_limit_pct": 5.0,
                "max_position_pct": 5.0,
                "max_exposure_pct": 80.0,
                "deployment_max_drawdown_pct": 10.0,
                "stale_data_block_orders": True,
                "stale_data_max_missed_slots": 1,
            },
        )(),
    )
    intent = OrderIntent(side="buy", qty=1.0, reason="test")
    result = run_risk_checks(
        intent,
        kill_switch_enabled=False,
        orders_this_minute=0,
        deployment_has_open_order=False,
        account_equity=10_000.0,
        day_start_equity=10_000.0,
        day_start_date=None,
        today=date.today(),
        deployment_exposure=0.0,
        last_price=100.0,
        strategy_profit_pct=0.0,
        peak_strategy_profit_pct=25.0,
        deployment_readiness={"update_status": "stale", "missed_slot_count": 2},
    )
    assert isinstance(result, RiskCheckResult)
    assert result.allowed is False
