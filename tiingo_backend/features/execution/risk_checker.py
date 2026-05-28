from dataclasses import dataclass
from datetime import date

from config import get_settings
from features.execution.signal_to_order import OrderIntent


@dataclass
class RiskCheckResult:
    allowed: bool
    reason: str | None = None


def check_kill_switch(kill_switch_enabled: bool) -> RiskCheckResult:
    if kill_switch_enabled:
        return RiskCheckResult(False, "Kill switch is enabled")
    return RiskCheckResult(True)


def check_rate_limit(orders_this_minute: int, max_orders: int) -> RiskCheckResult:
    if orders_this_minute >= max_orders:
        return RiskCheckResult(False, f"Order rate limit exceeded ({max_orders}/min)")
    return RiskCheckResult(True)


def check_open_orders(open_orders: list[dict], symbol: str) -> RiskCheckResult:
    symbol = symbol.upper()
    for order in open_orders:
        if order.get("symbol", "").upper() == symbol:
            return RiskCheckResult(False, f"Open order already exists for {symbol}")
    return RiskCheckResult(True)


def check_daily_loss(
    *,
    current_equity: float,
    day_start_equity: float | None,
    day_start_date: date | None,
    today: date,
    limit_pct: float,
) -> RiskCheckResult:
    if day_start_equity is None or day_start_date != today:
        return RiskCheckResult(True)
    if day_start_equity <= 0:
        return RiskCheckResult(True)
    loss_pct = ((day_start_equity - current_equity) / day_start_equity) * 100.0
    if loss_pct >= limit_pct:
        return RiskCheckResult(False, f"Daily loss limit reached ({loss_pct:.2f}%)")
    return RiskCheckResult(True)


def check_position_size(
    intent: OrderIntent,
    *,
    account_equity: float,
    last_price: float,
    max_position_pct: float,
) -> RiskCheckResult:
    if intent.side != "buy":
        return RiskCheckResult(True)
    notional = intent.qty * last_price
    if account_equity <= 0:
        return RiskCheckResult(False, "Account equity is zero")
    position_pct = (notional / account_equity) * 100.0
    if position_pct > max_position_pct:
        return RiskCheckResult(
            False,
            f"Position size {position_pct:.2f}% exceeds max {max_position_pct}%",
        )
    return RiskCheckResult(True)


def check_exposure(
    intent: OrderIntent,
    *,
    account_equity: float,
    positions: list[dict],
    last_price: float,
    max_exposure_pct: float,
) -> RiskCheckResult:
    if intent.side != "buy" or account_equity <= 0:
        return RiskCheckResult(True)
    current_exposure = sum(abs(float(p.get("market_value") or 0)) for p in positions)
    new_exposure = current_exposure + (intent.qty * last_price)
    exposure_pct = (new_exposure / account_equity) * 100.0
    if exposure_pct > max_exposure_pct:
        return RiskCheckResult(
            False,
            f"Portfolio exposure {exposure_pct:.2f}% exceeds max {max_exposure_pct}%",
        )
    return RiskCheckResult(True)


def run_risk_checks(
    intent: OrderIntent,
    *,
    symbol: str,
    kill_switch_enabled: bool,
    orders_this_minute: int,
    open_orders: list[dict],
    account_equity: float,
    day_start_equity: float | None,
    day_start_date: date | None,
    today: date,
    positions: list[dict],
    last_price: float,
) -> RiskCheckResult:
    settings = get_settings()
    checks = [
        check_kill_switch(kill_switch_enabled),
        check_rate_limit(orders_this_minute, settings.max_orders_per_minute),
        check_open_orders(open_orders, symbol),
        check_daily_loss(
            current_equity=account_equity,
            day_start_equity=day_start_equity,
            day_start_date=day_start_date,
            today=today,
            limit_pct=settings.daily_loss_limit_pct,
        ),
        check_position_size(
            intent,
            account_equity=account_equity,
            last_price=last_price,
            max_position_pct=settings.max_position_pct,
        ),
        check_exposure(
            intent,
            account_equity=account_equity,
            positions=positions,
            last_price=last_price,
            max_exposure_pct=settings.max_exposure_pct,
        ),
    ]
    for result in checks:
        if not result.allowed:
            return result
    return RiskCheckResult(True)
