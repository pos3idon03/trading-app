from dataclasses import dataclass, field
from datetime import datetime, timezone

from features.backtesting.simulator import (
    TradeRecord,
    _commission_amount,
    _slippage_adjusted_price,
)


def _format_trade_date(bar: dict) -> str:
    t = bar["time"]
    if isinstance(t, datetime):
        dt = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    if hasattr(t, "isoformat"):
        return t.isoformat()
    return str(t)


@dataclass
class MultiAssetPortfolioState:
    cash: float
    positions: dict[str, float] = field(default_factory=dict)
    entry_prices: dict[str, float] = field(default_factory=dict)
    entry_dates: dict[str, str] = field(default_factory=dict)
    target_weights: dict[str, float] = field(default_factory=dict)


@dataclass
class MultiAssetEquityPoint:
    date: str
    equity: float
    cash: float
    positions_value: float
    drawdown_pct: float


@dataclass
class MultiAssetTradeRecord(TradeRecord):
    symbol: str = ""
    exit_reason: str = ""


@dataclass
class MultiAssetSimulationResult:
    equity_curve: list[MultiAssetEquityPoint] = field(default_factory=list)
    trades: list[MultiAssetTradeRecord] = field(default_factory=list)
    final_equity: float = 0.0


def _position_qty(state: MultiAssetPortfolioState, symbol: str) -> float:
    return state.positions.get(symbol, 0.0)


def mark_multi_equity(
    state: MultiAssetPortfolioState,
    prices: dict[str, float],
    peak_equity: float,
) -> tuple[float, float]:
    positions_value = sum(
        qty * prices.get(sym, 0.0) for sym, qty in state.positions.items()
    )
    equity = state.cash + positions_value
    drawdown = 0.0 if peak_equity <= 0 else ((equity - peak_equity) / peak_equity) * 100.0
    return equity, drawdown


def buy_qty(
    state: MultiAssetPortfolioState,
    symbol: str,
    qty: float,
    price: float,
    bar: dict,
    commission_bps: float,
    slippage_bps: float = 0.0,
) -> None:
    if qty <= 0 or price <= 0:
        return
    fill_price = _slippage_adjusted_price(price, slippage_bps, side="buy")
    notional = qty * fill_price
    commission = _commission_amount(notional, commission_bps)
    total_cost = notional + commission
    if total_cost > state.cash:
        qty = max(0.0, (state.cash - commission) / fill_price)
        if qty <= 0:
            return
        notional = qty * fill_price
        commission = _commission_amount(notional, commission_bps)
        total_cost = notional + commission

    prev_qty = _position_qty(state, symbol)
    if prev_qty <= 0:
        state.entry_prices[symbol] = fill_price
        state.entry_dates[symbol] = _format_trade_date(bar)
    else:
        old_entry = state.entry_prices.get(symbol, fill_price)
        state.entry_prices[symbol] = (
            (old_entry * prev_qty) + (fill_price * qty)
        ) / (prev_qty + qty)

    state.positions[symbol] = prev_qty + qty
    state.cash -= total_cost


def sell_qty(
    state: MultiAssetPortfolioState,
    symbol: str,
    qty: float,
    price: float,
    bar: dict,
    commission_bps: float,
    trades: list[MultiAssetTradeRecord],
    slippage_bps: float = 0.0,
    *,
    exit_reason: str = "",
) -> None:
    held = _position_qty(state, symbol)
    if held <= 0 or qty <= 0 or price <= 0:
        return
    sell_qty_actual = min(qty, held)
    fill_price = _slippage_adjusted_price(price, slippage_bps, side="sell")
    notional = sell_qty_actual * fill_price
    commission = _commission_amount(notional, commission_bps)
    proceeds = notional - commission
    entry_price = state.entry_prices.get(symbol, fill_price)
    entry_date = state.entry_dates.get(symbol, _format_trade_date(bar))
    pnl = proceeds - (sell_qty_actual * entry_price)
    cost_basis = sell_qty_actual * entry_price
    pnl_pct = (pnl / cost_basis) * 100.0 if cost_basis > 0 else 0.0

    trades.append(
        MultiAssetTradeRecord(
            symbol=symbol,
            entry_date=entry_date,
            exit_date=_format_trade_date(bar),
            entry_price=round(entry_price, 4),
            exit_price=round(fill_price, 4),
            shares=round(sell_qty_actual, 6),
            pnl=round(pnl, 2),
            pnl_pct=round(pnl_pct, 2),
            exit_reason=exit_reason,
        )
    )
    state.cash += proceeds
    remaining = held - sell_qty_actual
    if remaining <= 1e-9:
        state.positions.pop(symbol, None)
        state.entry_prices.pop(symbol, None)
        state.entry_dates.pop(symbol, None)
    else:
        state.positions[symbol] = remaining


def force_liquidate_symbol(
    state: MultiAssetPortfolioState,
    symbol: str,
    price: float,
    bar: dict,
    commission_bps: float,
    trades: list[MultiAssetTradeRecord],
    slippage_bps: float = 0.0,
) -> None:
    qty = _position_qty(state, symbol)
    if qty <= 0:
        return
    sell_qty(
        state,
        symbol,
        qty,
        price,
        bar,
        commission_bps,
        trades,
        slippage_bps,
        exit_reason="delisted",
    )


def rebalance_to_targets(
    state: MultiAssetPortfolioState,
    targets: dict[str, float],
    prices: dict[str, float],
    bar: dict,
    commission_bps: float,
    trades: list[MultiAssetTradeRecord],
    slippage_bps: float = 0.0,
) -> None:
    equity, _ = mark_multi_equity(state, prices, 0.0)
    if equity <= 0:
        return

    for symbol, target_w in targets.items():
        price = prices.get(symbol, 0.0)
        if price <= 0:
            continue
        desired_value = equity * target_w
        current_qty = _position_qty(state, symbol)
        current_value = current_qty * price
        delta_value = desired_value - current_value
        if abs(delta_value) < 1.0:
            continue
        if delta_value > 0:
            buy_qty(state, symbol, delta_value / price, price, bar, commission_bps, slippage_bps)
        else:
            sell_qty(
                state,
                symbol,
                abs(delta_value) / price,
                price,
                bar,
                commission_bps,
                trades,
                slippage_bps,
                exit_reason="rebalance",
            )
