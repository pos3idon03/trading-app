"""Tests for the order manager."""
from unittest.mock import MagicMock, patch

import pytest

from features.execution.order_manager import (
    OrderPlan,
    _calculate_position_size,
    compute_buy_notional_usd,
    execute_order_plan,
    plan_order_from_signal,
    qty_from_notional,
)
from features.execution.risk_manager import PortfolioState, RiskCheckResult
from features.live_trading.signal_aggregator import AggregatedSignal


def _make_signal(action="BUY", confidence=0.7, symbol="AAPL"):
    return AggregatedSignal(
        symbol=symbol,
        timeframe="1h",
        action=action,
        confidence=confidence,
        technical_score=0.5,
        risk_score=0.3,
        ai_score=0.4,
        reasoning="test",
    )


def _make_portfolio(equity=100_000.0, position_values=None, position_quantities=None):
    return PortfolioState(
        equity=equity,
        cash=equity / 2,
        buying_power=equity,
        position_values=position_values or {},
        position_quantities=position_quantities or {},
        total_exposure=sum((position_values or {}).values()),
    )


class TestComputeBuyNotionalUsd:
    def test_legacy_equity_fraction(self):
        notional = compute_buy_notional_usd(
            100_000, 50_000, 0.75, position_fraction=0.02,
        )
        assert notional == pytest.approx(1500.0)

    def test_amount_only_capped_by_cash(self):
        notional = compute_buy_notional_usd(
            100_000, 500, 0.75, max_amount_per_position=200.0,
        )
        assert notional == 200.0

    def test_pct_only_uses_cash(self):
        notional = compute_buy_notional_usd(
            100_000, 20_000, 0.75, max_pct_of_capital=1.0,
        )
        assert notional == 200.0

    def test_both_takes_minimum(self):
        notional = compute_buy_notional_usd(
            100_000, 20_000, 0.75,
            max_amount_per_position=200.0,
            max_pct_of_capital=10.0,
        )
        assert notional == 200.0

    def test_zero_cash_returns_zero(self):
        assert compute_buy_notional_usd(100_000, 0, 0.75, max_amount_per_position=200.0) == 0.0


class TestQtyFromNotional:
    def test_crypto_precision(self):
        qty = qty_from_notional(80_000.0, 200.0, 8)
        assert qty == pytest.approx(0.0025, rel=1e-8)


class TestCalculatePositionSize:
    def test_basic_sizing(self):
        qty = _calculate_position_size(100_000, 150.0, 0.8, 0.02)
        assert qty > 0
        assert qty <= 100_000 * 0.02 / 150.0 + 0.01

    def test_zero_equity(self):
        assert _calculate_position_size(0, 150.0, 0.8, 0.02) == 0.0

    def test_zero_price(self):
        assert _calculate_position_size(100_000, 0, 0.8, 0.02) == 0.0

    def test_confidence_scales_size(self):
        high = _calculate_position_size(100_000, 150.0, 1.0, 0.02)
        low = _calculate_position_size(100_000, 150.0, 0.3, 0.02)
        assert high > low


class TestPlanOrderFromSignal:
    def test_buy_creates_plan(self):
        signal = _make_signal(action="BUY", confidence=0.8)
        portfolio = _make_portfolio()
        plan = plan_order_from_signal(signal, portfolio, 150.0)
        assert plan is not None
        assert plan.side == "buy"
        assert plan.qty > 0
        assert plan.symbol == "AAPL"

    def test_hold_returns_none(self):
        signal = _make_signal(action="HOLD")
        portfolio = _make_portfolio()
        plan = plan_order_from_signal(signal, portfolio, 150.0)
        assert plan is None

    def test_sell_with_position(self):
        signal = _make_signal(action="SELL")
        portfolio = _make_portfolio(
            position_values={"AAPL": 3000.0},
            position_quantities={"AAPL": 20.0},
        )
        plan = plan_order_from_signal(signal, portfolio, 150.0)
        assert plan is not None
        assert plan.side == "sell"
        assert plan.qty == 20.0

    def test_sell_without_position(self):
        signal = _make_signal(action="SELL")
        portfolio = _make_portfolio()
        plan = plan_order_from_signal(signal, portfolio, 150.0)
        assert plan is None

    def test_buy_with_max_amount(self):
        signal = _make_signal(action="BUY", confidence=0.75)
        portfolio = _make_portfolio(equity=100_000.0)
        portfolio.cash = 20_000.0
        plan = plan_order_from_signal(
            signal, portfolio, 80_000.0,
            max_amount_per_position=200.0,
            qty_decimals=8,
        )
        assert plan is not None
        assert plan.qty == pytest.approx(0.0025, rel=1e-8)

    def test_buy_with_max_pct_only(self):
        signal = _make_signal(action="BUY", confidence=0.75)
        portfolio = _make_portfolio(equity=100_000.0)
        portfolio.cash = 10_000.0
        plan = plan_order_from_signal(
            signal, portfolio, 50.0,
            max_pct_of_capital=1.0,
        )
        assert plan is not None
        assert plan.qty == pytest.approx(2.0)


class TestExecuteOrderPlan:
    @patch("features.execution.order_manager.get_risk_manager")
    @patch("features.execution.order_manager.submit_market_order")
    def test_approved_order(self, mock_submit, mock_risk_mgr):
        mock_risk_mgr.return_value.check_risk.return_value = RiskCheckResult(approved=True)
        mock_submit.return_value = MagicMock(order_id="test-1", status="accepted")

        plan = OrderPlan(symbol="AAPL", side="buy", qty=10, order_type="market", estimated_price=150.0)
        risk_result, order_result = execute_order_plan(plan)

        assert risk_result.approved
        assert order_result is not None
        mock_submit.assert_called_once()

    @patch("features.execution.order_manager.get_risk_manager")
    def test_rejected_order(self, mock_risk_mgr):
        mock_risk_mgr.return_value.check_risk.return_value = RiskCheckResult(
            approved=False, violations=["POSITION_SIZE: exceeds limit"]
        )

        plan = OrderPlan(symbol="AAPL", side="buy", qty=10, order_type="market", estimated_price=150.0)
        risk_result, order_result = execute_order_plan(plan)

        assert not risk_result.approved
        assert order_result is None
