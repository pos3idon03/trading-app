"""Tests for the risk manager."""
from datetime import datetime, timedelta, timezone

import pytest

from features.execution.risk_manager import (
    PortfolioState,
    RiskCheckResult,
    RiskConfig,
    RiskManager,
)


@pytest.fixture
def risk_manager():
    rm = RiskManager()
    rm._config = RiskConfig(
        max_position_pct=5.0,
        max_exposure_pct=80.0,
        daily_loss_limit_pct=5.0,
        max_orders_per_minute=10,
        kill_switch_active=False,
    )
    return rm


@pytest.fixture
def portfolio():
    return PortfolioState(
        equity=100_000.0,
        cash=50_000.0,
        buying_power=100_000.0,
        daily_pnl=0.0,
        daily_pnl_pct=0.0,
        position_values={"AAPL": 3_000.0},
        total_exposure=3_000.0,
    )


class TestKillSwitch:
    def test_kill_switch_blocks_all_trades(self, risk_manager, portfolio):
        risk_manager.update_portfolio(portfolio)
        risk_manager.activate_kill_switch()

        result = risk_manager.check_risk("AAPL", "buy", 10, 150.0)
        assert not result.approved
        assert any("KILL_SWITCH" in v for v in result.violations)

    def test_deactivate_allows_trades(self, risk_manager, portfolio):
        risk_manager.update_portfolio(portfolio)
        risk_manager.activate_kill_switch()
        risk_manager.deactivate_kill_switch()

        result = risk_manager.check_risk("AAPL", "buy", 1, 150.0)
        assert result.approved


class TestPositionSizeLimit:
    def test_within_limit(self, risk_manager, portfolio):
        risk_manager.update_portfolio(portfolio)
        result = risk_manager.check_risk("MSFT", "buy", 10, 100.0)
        assert result.approved

    def test_exceeds_limit(self, risk_manager, portfolio):
        risk_manager.update_portfolio(portfolio)
        result = risk_manager.check_risk("AAPL", "buy", 30, 150.0)
        assert not result.approved
        assert any("POSITION_SIZE" in v for v in result.violations)

    def test_new_symbol_within_limit(self, risk_manager, portfolio):
        risk_manager.update_portfolio(portfolio)
        result = risk_manager.check_risk("TSLA", "buy", 5, 200.0)
        assert result.approved


class TestExposureLimit:
    def test_within_exposure(self, risk_manager, portfolio):
        risk_manager.update_portfolio(portfolio)
        result = risk_manager.check_risk("MSFT", "buy", 10, 100.0)
        assert result.approved

    def test_exceeds_exposure(self, risk_manager, portfolio):
        portfolio.total_exposure = 79_000.0
        risk_manager.update_portfolio(portfolio)
        result = risk_manager.check_risk("MSFT", "buy", 30, 100.0)
        assert not result.approved
        assert any("EXPOSURE" in v for v in result.violations)


class TestDailyLossLimit:
    def test_no_loss_allows_trade(self, risk_manager, portfolio):
        risk_manager.update_portfolio(portfolio)
        result = risk_manager.check_risk("AAPL", "buy", 1, 150.0)
        assert result.approved

    def test_daily_loss_triggers_kill_switch(self, risk_manager, portfolio):
        portfolio.daily_pnl = -6000.0
        portfolio.daily_pnl_pct = -6.0
        risk_manager.update_portfolio(portfolio)

        result = risk_manager.check_risk("AAPL", "buy", 1, 150.0)
        assert not result.approved
        assert any("DAILY_LOSS" in v for v in result.violations)
        assert risk_manager.config.kill_switch_active


class TestRateLimit:
    def test_within_rate_limit(self, risk_manager, portfolio):
        risk_manager.update_portfolio(portfolio)
        for _ in range(5):
            result = risk_manager.check_risk("AAPL", "buy", 1, 150.0)
            assert result.approved

    def test_exceeds_rate_limit(self, risk_manager, portfolio):
        risk_manager.update_portfolio(portfolio)
        for _ in range(10):
            risk_manager.check_risk("AAPL", "buy", 1, 150.0)

        result = risk_manager.check_risk("AAPL", "buy", 1, 150.0)
        assert not result.approved
        assert any("RATE_LIMIT" in v for v in result.violations)


class TestConfigUpdate:
    def test_update_config(self, risk_manager):
        risk_manager.update_config(max_position_pct=10.0, max_orders_per_minute=20)
        assert risk_manager.config.max_position_pct == 10.0
        assert risk_manager.config.max_orders_per_minute == 20

    def test_config_to_dict(self, risk_manager):
        d = risk_manager.config.to_dict()
        assert "max_position_pct" in d
        assert "kill_switch_active" in d
