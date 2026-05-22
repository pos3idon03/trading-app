from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PortfolioState:
    cash: float
    shares: float = 0.0
    entry_price: float | None = None
    entry_date: str | None = None


@dataclass
class TradeRecord:
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    shares: float
    pnl: float
    pnl_pct: float


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


def buy_all_in(
    state: PortfolioState,
    price: float,
    bar: dict,
    commission_bps: float,
) -> None:
    if price <= 0 or state.cash <= 0:
        return

    commission = _commission_amount(state.cash, commission_bps)
    spendable = max(state.cash - commission, 0.0)
    shares = spendable / price
    if shares <= 0:
        return

    state.shares = shares
    state.cash = state.cash - commission - (shares * price)
    state.entry_price = price
    state.entry_date = _format_trade_date(bar)


def sell_all(
    state: PortfolioState,
    price: float,
    bar: dict,
    commission_bps: float,
    trades: list[TradeRecord],
) -> None:
    if state.shares <= 0 or price <= 0:
        return

    notional = state.shares * price
    commission = _commission_amount(notional, commission_bps)
    proceeds = notional - commission
    entry_price = state.entry_price or price
    entry_date = state.entry_date or _format_trade_date(bar)
    pnl = proceeds - (state.shares * entry_price)
    pnl_pct = (pnl / (state.shares * entry_price)) * 100.0 if entry_price > 0 else 0.0

    trades.append(
        TradeRecord(
            entry_date=entry_date,
            exit_date=_format_trade_date(bar),
            entry_price=round(entry_price, 4),
            exit_price=round(price, 4),
            shares=round(state.shares, 6),
            pnl=round(pnl, 2),
            pnl_pct=round(pnl_pct, 2),
        )
    )

    state.cash += proceeds
    state.shares = 0.0
    state.entry_price = None
    state.entry_date = None


def mark_equity(state: PortfolioState, bar: dict, peak_equity: float) -> tuple[float, float]:
    equity = state.cash + (state.shares * float(bar["close"]))
    drawdown = 0.0 if peak_equity <= 0 else ((equity - peak_equity) / peak_equity) * 100.0
    return equity, drawdown
