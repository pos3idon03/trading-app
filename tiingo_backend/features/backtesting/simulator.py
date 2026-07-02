from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PortfolioState:
    cash: float
    shares: float = 0.0
    entry_price: float | None = None
    entry_date: str | None = None
    entry_bar_index: int | None = None
    bracket_profit_level: float | None = None
    bracket_stop_level: float | None = None


@dataclass
class TradeRecord:
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    shares: float
    pnl: float
    pnl_pct: float
    exit_reason: str = ""


@dataclass
class EquityPoint:
    date: str
    equity: float
    cash: float
    shares: float
    drawdown_pct: float


@dataclass
class SimulationResult:
    equity_curve: list[EquityPoint] = field(default_factory=list)
    trades: list[TradeRecord] = field(default_factory=list)
    final_equity: float = 0.0


def _format_trade_date(bar: dict) -> str:
    t = bar["time"]
    if isinstance(t, datetime):
        dt = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    if hasattr(t, "isoformat"):
        return t.isoformat()
    return str(t)


def apply_corporate_actions(state: PortfolioState, bar: dict) -> None:
    """No-op: Tiingo EOD bars use adjusted OHLCV; splits/dividends are already in prices."""
    return


def _commission_amount(notional: float, commission_bps: float) -> float:
    return notional * (commission_bps / 10_000.0)


def _slippage_adjusted_price(price: float, slippage_bps: float, *, side: str) -> float:
    if slippage_bps <= 0 or price <= 0:
        return price
    factor = slippage_bps / 10_000.0
    if side == "buy":
        return price * (1.0 + factor)
    return price * (1.0 - factor)


def buy_all_in(
    state: PortfolioState,
    price: float,
    bar: dict,
    commission_bps: float,
    slippage_bps: float = 0.0,
) -> None:
    if price <= 0 or state.cash <= 0:
        return

    fill_price = _slippage_adjusted_price(price, slippage_bps, side="buy")
    commission = _commission_amount(state.cash, commission_bps)
    spendable = max(state.cash - commission, 0.0)
    shares = spendable / fill_price
    if shares <= 0:
        return

    state.shares = shares
    state.cash = state.cash - commission - (shares * fill_price)
    state.entry_price = fill_price
    state.entry_date = _format_trade_date(bar)


def buy_all_in_at_bar(
    state: PortfolioState,
    price: float,
    bar: dict,
    bar_index: int,
    commission_bps: float,
    slippage_bps: float = 0.0,
) -> None:
    buy_all_in(state, price, bar, commission_bps, slippage_bps)
    if state.shares > 0:
        state.entry_bar_index = bar_index


def sell_all(
    state: PortfolioState,
    price: float,
    bar: dict,
    commission_bps: float,
    trades: list[TradeRecord],
    slippage_bps: float = 0.0,
    *,
    exit_reason: str = "signal",
) -> None:
    if state.shares <= 0 or price <= 0:
        return

    fill_price = _slippage_adjusted_price(price, slippage_bps, side="sell")
    notional = state.shares * fill_price
    commission = _commission_amount(notional, commission_bps)
    proceeds = notional - commission
    entry_price = state.entry_price or fill_price
    entry_date = state.entry_date or _format_trade_date(bar)
    pnl = proceeds - (state.shares * entry_price)
    pnl_pct = (pnl / (state.shares * entry_price)) * 100.0 if entry_price > 0 else 0.0

    trades.append(
        TradeRecord(
            entry_date=entry_date,
            exit_date=_format_trade_date(bar),
            entry_price=round(entry_price, 4),
            exit_price=round(fill_price, 4),
            shares=round(state.shares, 6),
            pnl=round(pnl, 2),
            pnl_pct=round(pnl_pct, 2),
            exit_reason=exit_reason,
        )
    )

    state.cash += proceeds
    state.shares = 0.0
    state.entry_price = None
    state.entry_date = None
    state.entry_bar_index = None
    state.bracket_profit_level = None
    state.bracket_stop_level = None


def mark_equity(state: PortfolioState, bar: dict, peak_equity: float) -> tuple[float, float]:
    equity = state.cash + (state.shares * float(bar["close"]))
    drawdown = 0.0 if peak_equity <= 0 else ((equity - peak_equity) / peak_equity) * 100.0
    return equity, drawdown
