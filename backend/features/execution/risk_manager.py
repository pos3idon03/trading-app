"""Hardcoded risk management kill-switch layer.

Every order must pass through check_risk() before submission.
This module is the last line of defense — it cannot be overridden by AI or strategy logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import get_settings
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RiskConfig:
    max_position_pct: float = 5.0
    max_exposure_pct: float = 80.0
    daily_loss_limit_pct: float = 5.0
    max_orders_per_minute: int = 10
    kill_switch_active: bool = False

    def to_dict(self) -> dict:
        return {
            "max_position_pct": self.max_position_pct,
            "max_exposure_pct": self.max_exposure_pct,
            "daily_loss_limit_pct": self.daily_loss_limit_pct,
            "max_orders_per_minute": self.max_orders_per_minute,
            "kill_switch_active": self.kill_switch_active,
        }


@dataclass
class RiskCheckResult:
    approved: bool
    violations: list[str] = field(default_factory=list)


@dataclass
class PortfolioState:
    equity: float
    cash: float
    buying_power: float
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    position_values: dict[str, float] = field(default_factory=dict)
    total_exposure: float = 0.0


class RiskManager:
    """Hardcoded risk management — prevents dangerous trades."""

    def __init__(self) -> None:
        settings = get_settings()
        self._config = RiskConfig(
            max_position_pct=settings.max_position_pct,
            max_exposure_pct=settings.max_exposure_pct,
            daily_loss_limit_pct=settings.daily_loss_limit_pct,
            max_orders_per_minute=settings.max_orders_per_minute,
        )
        self._order_timestamps: list[datetime] = []
        self._portfolio: PortfolioState | None = None

    @property
    def config(self) -> RiskConfig:
        return self._config

    def update_config(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self._config, key) and value is not None:
                setattr(self._config, key, value)
        logger.info("risk_config_updated", config=self._config.to_dict())

    def activate_kill_switch(self) -> None:
        self._config.kill_switch_active = True
        logger.warning("kill_switch_activated")

    def deactivate_kill_switch(self) -> None:
        self._config.kill_switch_active = False
        logger.info("kill_switch_deactivated")

    def update_portfolio(self, portfolio: PortfolioState) -> None:
        self._portfolio = portfolio

    def check_risk(
        self,
        symbol: str,
        side: str,
        qty: float,
        estimated_price: float,
    ) -> RiskCheckResult:
        """Run all risk checks. Returns approved=False if ANY check fails."""
        violations: list[str] = []

        self._check_kill_switch(violations)
        self._check_trading_mode(violations)
        self._check_rate_limit(violations)

        if self._portfolio:
            self._check_position_size(symbol, qty, estimated_price, violations)
            self._check_total_exposure(qty, estimated_price, side, violations)
            self._check_daily_loss_limit(violations)

        if not violations:
            self._record_order_timestamp()

        approved = len(violations) == 0
        if not approved:
            logger.warning(
                "risk_check_failed",
                symbol=symbol,
                side=side,
                qty=qty,
                violations=violations,
            )

        return RiskCheckResult(approved=approved, violations=violations)

    def _check_kill_switch(self, violations: list[str]) -> None:
        if self._config.kill_switch_active:
            violations.append("KILL_SWITCH: Global kill switch is active — all trading halted")

    def _check_trading_mode(self, violations: list[str]) -> None:
        settings = get_settings()
        if settings.trading_mode == "disabled":
            violations.append("TRADING_DISABLED: Trading mode is set to disabled")

    def _check_rate_limit(self, violations: list[str]) -> None:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=1)
        self._order_timestamps = [t for t in self._order_timestamps if t > cutoff]

        if len(self._order_timestamps) >= self._config.max_orders_per_minute:
            violations.append(
                f"RATE_LIMIT: {len(self._order_timestamps)} orders in last minute "
                f"(max {self._config.max_orders_per_minute})"
            )

    def _check_position_size(
        self, symbol: str, qty: float, price: float, violations: list[str],
    ) -> None:
        if self._portfolio is None or self._portfolio.equity <= 0:
            return

        order_value = qty * price
        existing_value = self._portfolio.position_values.get(symbol, 0.0)
        total_position = existing_value + order_value
        position_pct = (total_position / self._portfolio.equity) * 100

        if position_pct > self._config.max_position_pct:
            violations.append(
                f"POSITION_SIZE: {symbol} would be {position_pct:.1f}% of portfolio "
                f"(max {self._config.max_position_pct}%)"
            )

    def _check_total_exposure(
        self, qty: float, price: float, side: str, violations: list[str],
    ) -> None:
        if self._portfolio is None or self._portfolio.equity <= 0:
            return

        order_value = qty * price if side.lower() == "buy" else 0.0
        projected_exposure = self._portfolio.total_exposure + order_value
        exposure_pct = (projected_exposure / self._portfolio.equity) * 100

        if exposure_pct > self._config.max_exposure_pct:
            violations.append(
                f"EXPOSURE: Total exposure would be {exposure_pct:.1f}% "
                f"(max {self._config.max_exposure_pct}%)"
            )

    def _check_daily_loss_limit(self, violations: list[str]) -> None:
        if self._portfolio is None or self._portfolio.equity <= 0:
            return

        if abs(self._portfolio.daily_pnl_pct) > self._config.daily_loss_limit_pct:
            if self._portfolio.daily_pnl_pct < 0:
                violations.append(
                    f"DAILY_LOSS: Portfolio down {abs(self._portfolio.daily_pnl_pct):.2f}% today "
                    f"(limit {self._config.daily_loss_limit_pct}%) — trading halted"
                )
                self._config.kill_switch_active = True
                logger.warning("daily_loss_kill_switch_triggered")

    def _record_order_timestamp(self) -> None:
        self._order_timestamps.append(datetime.now(timezone.utc))


_instance: RiskManager | None = None


def get_risk_manager() -> RiskManager:
    global _instance
    if _instance is None:
        _instance = RiskManager()
    return _instance
