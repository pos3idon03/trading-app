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


def check_deployment_open_order(has_open: bool) -> RiskCheckResult:
    if has_open:
        return RiskCheckResult(False, "Open order already exists for this deployment")
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
    deployment_exposure: float,
    last_price: float,
    max_exposure_pct: float,
) -> RiskCheckResult:
    # Deployment-attributed exposure only; untracked Alpaca holdings are ignored here.
    if intent.side != "buy" or account_equity <= 0:
        return RiskCheckResult(True)
    new_exposure = deployment_exposure + (intent.qty * last_price)
    exposure_pct = (new_exposure / account_equity) * 100.0
    if exposure_pct > max_exposure_pct:
        return RiskCheckResult(
            False,
            f"Portfolio exposure {exposure_pct:.2f}% exceeds max {max_exposure_pct}%",
        )
    return RiskCheckResult(True)


def check_deployment_drawdown(
    *,
    strategy_profit_pct: float | None,
    peak_strategy_profit_pct: float | None,
    max_drawdown_pct: float,
) -> RiskCheckResult:
    if strategy_profit_pct is None or peak_strategy_profit_pct is None:
        return RiskCheckResult(True)
    drawdown = float(peak_strategy_profit_pct) - float(strategy_profit_pct)
    if drawdown >= max_drawdown_pct:
        return RiskCheckResult(
            False,
            f"Deployment drawdown limit reached ({drawdown:.2f}% from peak)",
        )
    return RiskCheckResult(True)


def check_stale_data(
    readiness: dict | None,
    *,
    enabled: bool,
    max_missed_slots: int,
) -> RiskCheckResult:
    if not enabled or not readiness:
        return RiskCheckResult(True)
    if readiness.get("update_status") != "stale":
        return RiskCheckResult(True)
    missed = int(readiness.get("missed_slot_count") or 0)
    if missed >= max_missed_slots:
        return RiskCheckResult(
            False,
            f"Stale market data ({missed} missed evaluation slot(s))",
        )
    return RiskCheckResult(True)


def check_sentiment_guardrail(
    intent: OrderIntent,
    *,
    avg_score_1d: float | None,
    article_count_1d: int,
    enabled: bool,
    min_score: float,
    min_articles: int,
) -> RiskCheckResult:
    if not enabled or intent.side != "buy":
        return RiskCheckResult(True)
    if avg_score_1d is None or article_count_1d < min_articles:
        return RiskCheckResult(True)
    if avg_score_1d < min_score:
        return RiskCheckResult(
            False,
            f"News sentiment guardrail blocked buy "
            f"(avg_score={avg_score_1d:.2f}, articles={article_count_1d})",
        )
    return RiskCheckResult(True)


def run_risk_checks(
    intent: OrderIntent,
    *,
    kill_switch_enabled: bool,
    orders_this_minute: int,
    deployment_has_open_order: bool,
    account_equity: float,
    day_start_equity: float | None,
    day_start_date: date | None,
    today: date,
    deployment_exposure: float,
    last_price: float,
    sentiment_guardrail_enabled: bool = False,
    sentiment_avg_score_1d: float | None = None,
    sentiment_article_count_1d: int = 0,
    sentiment_min_score: float = -0.5,
    sentiment_min_articles: int = 3,
    strategy_profit_pct: float | None = None,
    peak_strategy_profit_pct: float | None = None,
    deployment_readiness: dict | None = None,
) -> RiskCheckResult:
    settings = get_settings()
    checks = [
        check_kill_switch(kill_switch_enabled),
        check_rate_limit(orders_this_minute, settings.max_orders_per_minute),
        check_deployment_open_order(deployment_has_open_order),
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
            deployment_exposure=deployment_exposure,
            last_price=last_price,
            max_exposure_pct=settings.max_exposure_pct,
        ),
        check_sentiment_guardrail(
            intent,
            avg_score_1d=sentiment_avg_score_1d,
            article_count_1d=sentiment_article_count_1d,
            enabled=sentiment_guardrail_enabled,
            min_score=sentiment_min_score,
            min_articles=sentiment_min_articles,
        ),
        check_deployment_drawdown(
            strategy_profit_pct=strategy_profit_pct,
            peak_strategy_profit_pct=peak_strategy_profit_pct,
            max_drawdown_pct=settings.deployment_max_drawdown_pct,
        ),
        check_stale_data(
            deployment_readiness,
            enabled=settings.stale_data_block_orders,
            max_missed_slots=settings.stale_data_max_missed_slots,
        ),
    ]
    for result in checks:
        if not result.allowed:
            return result
    return RiskCheckResult(True)
