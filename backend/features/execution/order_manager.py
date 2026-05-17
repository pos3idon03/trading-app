"""Order manager: translates signals into orders, applies risk checks, and executes."""
from __future__ import annotations

from dataclasses import dataclass

from features.execution.broker_client import (
    OrderResult,
    submit_limit_order,
    submit_market_order,
    submit_stop_loss,
)
from features.execution.risk_manager import PortfolioState, RiskCheckResult, get_risk_manager
from features.live_trading.signal_aggregator import AggregatedSignal
from utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_POSITION_FRACTION = 0.02
STOP_LOSS_PCT = 0.03
CRYPTO_QTY_DECIMALS = 8
EQUITY_QTY_DECIMALS = 2


@dataclass
class OrderPlan:
    symbol: str
    side: str
    qty: float
    order_type: str
    limit_price: float | None = None
    stop_price: float | None = None
    estimated_price: float = 0.0


def qty_decimals_for_asset_type(asset_type: str | None) -> int:
    if (asset_type or "stock").lower() == "crypto":
        return CRYPTO_QTY_DECIMALS
    return EQUITY_QTY_DECIMALS


def compute_buy_notional_usd(
    equity: float,
    cash: float,
    confidence: float,
    max_amount_per_position: float | None = None,
    max_pct_of_capital: float | None = None,
    position_fraction: float = DEFAULT_POSITION_FRACTION,
) -> float:
    """Dollar notional for a buy; capped by available cash."""
    if cash <= 0:
        return 0.0

    if max_amount_per_position is None and max_pct_of_capital is None:
        scaled_fraction = position_fraction * min(1.0, confidence)
        return min(equity * scaled_fraction, cash)

    pct_cap = (
        (max_pct_of_capital / 100.0) * cash
        if max_pct_of_capital is not None
        else None
    )

    if max_amount_per_position is not None and pct_cap is not None:
        notional = min(max_amount_per_position, pct_cap)
    elif max_amount_per_position is not None:
        notional = max_amount_per_position
    else:
        notional = pct_cap

    return min(notional, cash) if notional is not None else 0.0


def qty_from_notional(price: float, notional: float, decimals: int) -> float:
    if price <= 0 or notional <= 0:
        return 0.0
    return round(notional / price, decimals)


def plan_order_from_signal(
    signal: AggregatedSignal,
    portfolio: PortfolioState,
    current_price: float,
    position_fraction: float = DEFAULT_POSITION_FRACTION,
    max_amount_per_position: float | None = None,
    max_pct_of_capital: float | None = None,
    qty_decimals: int = EQUITY_QTY_DECIMALS,
) -> OrderPlan | None:
    """Convert an aggregated signal into an order plan with position sizing."""
    if signal.action == "HOLD":
        return None

    side = "buy" if signal.action == "BUY" else "sell"

    if side == "sell":
        existing_qty = _get_position_qty(portfolio, signal.symbol)
        if existing_qty <= 0:
            logger.info("sell_no_position", symbol=signal.symbol)
            return None
        return OrderPlan(
            symbol=signal.symbol,
            side=side,
            qty=existing_qty,
            order_type="market",
            estimated_price=current_price,
        )

    if max_amount_per_position is None and max_pct_of_capital is None:
        qty = _calculate_position_size(
            portfolio.equity, current_price, signal.confidence, position_fraction,
        )
    else:
        notional = compute_buy_notional_usd(
            portfolio.equity,
            portfolio.cash,
            signal.confidence,
            max_amount_per_position=max_amount_per_position,
            max_pct_of_capital=max_pct_of_capital,
            position_fraction=position_fraction,
        )
        qty = qty_from_notional(current_price, notional, qty_decimals)

    if qty <= 0:
        return None

    return OrderPlan(
        symbol=signal.symbol,
        side=side,
        qty=qty,
        order_type="market",
        estimated_price=current_price,
    )


def _calculate_position_size(
    equity: float,
    price: float,
    confidence: float,
    base_fraction: float,
) -> float:
    """Fixed-fraction sizing scaled by signal confidence."""
    if equity <= 0 or price <= 0:
        return 0.0

    scaled_fraction = base_fraction * min(1.0, confidence)
    dollar_amount = equity * scaled_fraction
    qty = dollar_amount / price
    return round(max(0, qty), EQUITY_QTY_DECIMALS)


def _get_position_qty(portfolio: PortfolioState, symbol: str) -> float:
    return portfolio.position_quantities.get(symbol, 0.0)


def execute_order_plan(plan: OrderPlan) -> tuple[RiskCheckResult, OrderResult | None]:
    """Run risk checks, then execute the order if approved."""
    risk_mgr = get_risk_manager()
    risk_result = risk_mgr.check_risk(
        symbol=plan.symbol,
        side=plan.side,
        qty=plan.qty,
        estimated_price=plan.estimated_price,
    )

    if not risk_result.approved:
        logger.warning("order_rejected_by_risk", symbol=plan.symbol, violations=risk_result.violations)
        return risk_result, None

    order_result = _submit_order(plan)
    return risk_result, order_result


def _submit_order(plan: OrderPlan) -> OrderResult:
    if plan.order_type == "limit" and plan.limit_price is not None:
        return submit_limit_order(plan.symbol, plan.qty, plan.side, plan.limit_price)
    elif plan.order_type == "stop" and plan.stop_price is not None:
        return submit_stop_loss(plan.symbol, plan.qty, plan.stop_price)
    else:
        return submit_market_order(plan.symbol, plan.qty, plan.side)


def place_stop_loss_for_position(symbol: str, qty: float, entry_price: float) -> OrderResult | None:
    """Automatically place a stop-loss after a buy fill."""
    stop_price = round(entry_price * (1 - STOP_LOSS_PCT), 2)
    risk_mgr = get_risk_manager()

    if risk_mgr.config.kill_switch_active:
        logger.warning("stop_loss_blocked_kill_switch", symbol=symbol)
        return None

    return submit_stop_loss(symbol, qty, stop_price)
