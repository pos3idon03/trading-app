"""Alpaca broker client wrapper for paper trading execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config import get_settings
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str
    qty: float
    order_type: str
    status: str
    filled_price: float | None = None
    filled_qty: float | None = None
    limit_price: float | None = None
    stop_price: float | None = None
    error: str | None = None


@dataclass
class Position:
    symbol: str
    qty: float
    market_value: float
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class AccountInfo:
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    day_trade_count: int


def _get_trading_client():
    from alpaca.trading.client import TradingClient

    settings = get_settings()
    return TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=True,
    )


def _tif_for_symbol(symbol: str, TimeInForce):
    """Alpaca crypto requires GTC; equities use DAY."""
    return TimeInForce.GTC if "/" in symbol else TimeInForce.DAY


def submit_market_order(symbol: str, qty: float, side: str) -> OrderResult:
    """Submit a market order via Alpaca paper trading."""
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    client = _get_trading_client()
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

    try:
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=_tif_for_symbol(symbol, TimeInForce),
        )
        order = client.submit_order(req)
        logger.info("market_order_submitted", symbol=symbol, side=side, qty=qty, order_id=str(order.id))
        return _order_to_result(order)
    except Exception as exc:
        logger.error("market_order_failed", symbol=symbol, error=str(exc))
        return OrderResult(
            order_id="", symbol=symbol, side=side, qty=qty,
            order_type="market", status="rejected", error=str(exc),
        )


def submit_limit_order(symbol: str, qty: float, side: str, limit_price: float) -> OrderResult:
    """Submit a limit order via Alpaca paper trading."""
    from alpaca.trading.requests import LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    client = _get_trading_client()
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

    try:
        req = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=_tif_for_symbol(symbol, TimeInForce),
            limit_price=limit_price,
        )
        order = client.submit_order(req)
        logger.info("limit_order_submitted", symbol=symbol, side=side, qty=qty, limit=limit_price)
        return _order_to_result(order)
    except Exception as exc:
        logger.error("limit_order_failed", symbol=symbol, error=str(exc))
        return OrderResult(
            order_id="", symbol=symbol, side=side, qty=qty,
            order_type="limit", status="rejected", limit_price=limit_price, error=str(exc),
        )


def submit_stop_loss(symbol: str, qty: float, stop_price: float) -> OrderResult:
    """Submit a stop-loss sell order via Alpaca paper trading."""
    from alpaca.trading.requests import StopOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    client = _get_trading_client()
    try:
        req = StopOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.GTC,
            stop_price=stop_price,
        )
        order = client.submit_order(req)
        logger.info("stop_loss_submitted", symbol=symbol, qty=qty, stop=stop_price)
        return _order_to_result(order)
    except Exception as exc:
        logger.error("stop_loss_failed", symbol=symbol, error=str(exc))
        return OrderResult(
            order_id="", symbol=symbol, side="sell", qty=qty,
            order_type="stop", status="rejected", stop_price=stop_price, error=str(exc),
        )


def cancel_order(alpaca_order_id: str) -> bool:
    client = _get_trading_client()
    try:
        client.cancel_order_by_id(alpaca_order_id)
        logger.info("order_cancelled", alpaca_order_id=alpaca_order_id)
        return True
    except Exception as exc:
        logger.error("cancel_order_failed", alpaca_order_id=alpaca_order_id, error=str(exc))
        return False


def get_positions() -> list[Position]:
    client = _get_trading_client()
    try:
        raw_positions = client.get_all_positions()
        return [_raw_to_position(p) for p in raw_positions]
    except Exception as exc:
        logger.error("get_positions_failed", error=str(exc))
        return []


def has_position(symbol: str) -> bool:
    """Return True if we currently hold a non-zero position in symbol."""
    return any(p.symbol == symbol and p.qty != 0 for p in get_positions())


def get_account() -> AccountInfo | None:
    client = _get_trading_client()
    try:
        acct = client.get_account()
        return AccountInfo(
            equity=float(acct.equity),
            cash=float(acct.cash),
            buying_power=float(acct.buying_power),
            portfolio_value=float(acct.portfolio_value),
            day_trade_count=int(acct.daytrade_count),
        )
    except Exception as exc:
        logger.error("get_account_failed", error=str(exc))
        return None


def _order_to_result(order) -> OrderResult:
    return OrderResult(
        order_id=str(order.id),
        symbol=order.symbol,
        side=str(order.side.value) if hasattr(order.side, "value") else str(order.side),
        qty=float(order.qty) if order.qty else 0.0,
        order_type=str(order.order_type.value) if hasattr(order.order_type, "value") else str(order.order_type),
        status=str(order.status.value) if hasattr(order.status, "value") else str(order.status),
        filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
        filled_qty=float(order.filled_qty) if order.filled_qty else None,
        limit_price=float(order.limit_price) if order.limit_price else None,
        stop_price=float(order.stop_price) if order.stop_price else None,
    )


def _raw_to_position(p) -> Position:
    return Position(
        symbol=p.symbol,
        qty=float(p.qty),
        market_value=float(p.market_value),
        avg_entry_price=float(p.avg_entry_price),
        current_price=float(p.current_price),
        unrealized_pnl=float(p.unrealized_pl),
        unrealized_pnl_pct=float(p.unrealized_plpc),
    )
