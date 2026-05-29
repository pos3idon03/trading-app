from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dal import execution_order_dal, instrument_dal, ohlcv_dal, trading_deployment_dal
from features.execution.deployment_metrics import filled_orders_chronological
from features.execution.deployment_position import effective_filled_qty
from features.market_data.performance import _close_on_or_before, _pct_change

_BENCHMARK_ETF_SYMBOLS = frozenset({"QQQ", "VOO"})
_STORED_BENCHMARK_SOURCE = "tiingo_eod"
_BENCHMARK_LOOKBACK_BUFFER_DAYS = 14
_START_PRICE_TAIL_LIMIT = 30


@dataclass(frozen=True)
class PeriodPnl:
    amount: float
    pct: float | None


@dataclass(frozen=True)
class PortfolioPeriodSummary:
    closed_pnl: PeriodPnl
    open_pnl: PeriodPnl
    qqq_return_pct: float | None
    voo_return_pct: float | None
    start: datetime
    end: datetime


def resolve_portfolio_period(
    start: datetime | None,
    end: datetime | None,
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    effective_end = _ensure_utc(end) if end is not None else now
    if start is not None:
        effective_start = _ensure_utc(start)
    else:
        effective_start = datetime(effective_end.year, 1, 1, tzinfo=timezone.utc)
    if effective_start > effective_end:
        raise ValueError("start must be before or equal to end")
    return effective_start, effective_end


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _in_period(value: datetime | None, start: datetime, end: datetime) -> bool:
    if value is None:
        return False
    ts = _ensure_utc(value)
    return start <= ts <= end


def compute_closed_pnl_for_period(
    orders: list[dict],
    start: datetime,
    end: datetime,
) -> PeriodPnl:
    lots: list[list[float]] = []
    realized = 0.0
    closed_cost_basis = 0.0

    for order in filled_orders_chronological(orders):
        qty = effective_filled_qty(order)
        price = float(order.get("filled_avg_price") or 0)
        side = (order.get("side") or "").lower()
        if side == "buy":
            lots.append([qty, price])
            continue
        if side != "sell":
            continue

        if not _in_period(order.get("filled_at"), start, end):
            remaining_skip = qty
            while remaining_skip > 1e-8 and lots:
                lot_qty, _ = lots[0]
                take = min(remaining_skip, lot_qty)
                remaining_skip -= take
                if lot_qty - take <= 1e-8:
                    lots.pop(0)
                else:
                    lots[0][0] = lot_qty - take
            continue

        remaining = qty
        while remaining > 1e-8 and lots:
            lot_qty, lot_price = lots[0]
            take = min(remaining, lot_qty)
            realized += take * (price - lot_price)
            closed_cost_basis += take * lot_price
            remaining -= take
            if lot_qty - take <= 1e-8:
                lots.pop(0)
            else:
                lots[0][0] = lot_qty - take

    pct = (realized / closed_cost_basis * 100.0) if closed_cost_basis > 0 else None
    return PeriodPnl(amount=realized, pct=round(pct, 2) if pct is not None else None)


def compute_open_period_pnl(
    positions: list[dict],
    start_prices: dict[str, float],
) -> PeriodPnl:
    period_pl = 0.0
    basis = 0.0
    for row in positions:
        qty = float(row.get("qty") or 0)
        if qty <= 0:
            continue
        symbol = (row.get("symbol") or "").upper()
        current_price = float(row.get("current_price") or 0)
        start_price = start_prices.get(symbol)
        if start_price is None or start_price <= 0:
            start_price = float(row.get("avg_entry_price") or 0)
        if start_price <= 0:
            start_price = current_price
        period_pl += qty * (current_price - start_price)
        basis += qty * start_price
    pct = (period_pl / basis * 100.0) if basis > 0 else None
    return PeriodPnl(amount=period_pl, pct=round(pct, 2) if pct is not None else None)


def compute_row_period_pl(row: dict, start_prices: dict[str, float]) -> float:
    qty = float(row.get("qty") or 0)
    if qty <= 0:
        return 0.0
    symbol = (row.get("symbol") or "").upper()
    current_price = float(row.get("current_price") or 0)
    start_price = start_prices.get(symbol)
    if start_price is None or start_price <= 0:
        start_price = float(row.get("avg_entry_price") or 0)
    if start_price <= 0:
        start_price = current_price
    return qty * (current_price - start_price)


def period_pl_by_position_key(
    deployment_rows: list[dict],
    untracked_rows: list[dict],
    start_prices: dict[str, float],
) -> dict[str, float]:
    result: dict[str, float] = {}
    for row in deployment_rows:
        key = str(row["deployment_id"])
        result[key] = compute_row_period_pl(row, start_prices)
    for index, row in enumerate(untracked_rows):
        key = f"untracked:{row['symbol']}:{index}"
        result[key] = compute_row_period_pl(row, start_prices)
    return result


async def load_start_prices(
    session: AsyncSession,
    symbols: set[str],
    start: datetime,
) -> dict[str, float]:
    target = start.date() if isinstance(start, datetime) else start
    effective_start = _ensure_utc(start)
    prices: dict[str, float] = {}
    for symbol in symbols:
        instrument = await instrument_dal.get_by_symbol(session, symbol)
        if not instrument:
            continue
        bars, _ = await ohlcv_dal.get_bars(
            session,
            instrument["id"],
            "1d",
            source=_STORED_BENCHMARK_SOURCE,
            end=effective_start,
            limit=_START_PRICE_TAIL_LIMIT,
            fetch_tail=True,
        )
        if not bars:
            bars, _ = await ohlcv_dal.get_bars(
                session,
                instrument["id"],
                "1d",
                end=effective_start,
                limit=_START_PRICE_TAIL_LIMIT,
                fetch_tail=True,
            )
        if not bars:
            continue
        sorted_bars = sorted(bars, key=lambda bar: bar["time"])
        close = _close_on_or_before(sorted_bars, target)
        if close is not None:
            prices[symbol.upper()] = close
    return prices


async def load_stored_etf_daily_bars(
    session: AsyncSession,
    symbol: str,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """Load ingested 1d OHLCV bars for benchmark ETFs from the database."""
    instrument = await instrument_dal.get_by_symbol(session, symbol.upper())
    if not instrument:
        return []

    lookback_start = _ensure_utc(start) - timedelta(days=_BENCHMARK_LOOKBACK_BUFFER_DAYS)
    effective_end = _ensure_utc(end)
    bars, _ = await ohlcv_dal.get_bars(
        session,
        instrument["id"],
        "1d",
        source=_STORED_BENCHMARK_SOURCE,
        start=lookback_start,
        end=effective_end,
        limit=5000,
    )
    if bars:
        return bars

    bars, _ = await ohlcv_dal.get_bars(
        session,
        instrument["id"],
        "1d",
        start=lookback_start,
        end=effective_end,
        limit=5000,
    )
    return bars


def compute_period_return_from_bars(
    bars: list[dict],
    start: datetime,
    end: datetime,
) -> float | None:
    if not bars:
        return None
    sorted_bars = sorted(bars, key=lambda bar: bar["time"])
    start_date = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end
    ref_close = _close_on_or_before(sorted_bars, start_date)
    end_close = _close_on_or_before(sorted_bars, end_date)
    if ref_close is None or end_close is None or ref_close <= 0:
        return None
    return round(_pct_change(end_close, ref_close), 2)


async def compute_benchmark_return(
    session: AsyncSession,
    symbol: str,
    start: datetime,
    end: datetime,
) -> float | None:
    normalized = symbol.upper()
    if normalized not in _BENCHMARK_ETF_SYMBOLS:
        return None
    bars = await load_stored_etf_daily_bars(session, normalized, start, end)
    return compute_period_return_from_bars(bars, start, end)


async def build_portfolio_period_summary(
    session: AsyncSession,
    *,
    deployment_rows: list[dict],
    untracked_rows: list[dict],
    start: datetime | None = None,
    end: datetime | None = None,
) -> tuple[PortfolioPeriodSummary, dict[str, float]]:
    effective_start, effective_end = resolve_portfolio_period(start, end)
    deployments = await trading_deployment_dal.list_deployments_enriched(session, limit=500)
    deployment_ids = [row["id"] for row in deployments]
    orders = await execution_order_dal.list_filled_orders_for_deployments(
        session,
        deployment_ids,
    )
    closed_pnl = compute_closed_pnl_for_period(orders, effective_start, effective_end)

    open_positions = deployment_rows + untracked_rows
    symbols = {(row.get("symbol") or "").upper() for row in open_positions if row.get("symbol")}
    start_prices = await load_start_prices(session, symbols, effective_start)
    open_pnl = compute_open_period_pnl(open_positions, start_prices)

    qqq_return = await compute_benchmark_return(session, "QQQ", effective_start, effective_end)
    voo_return = await compute_benchmark_return(session, "VOO", effective_start, effective_end)

    period_pl_map = period_pl_by_position_key(deployment_rows, untracked_rows, start_prices)
    summary = PortfolioPeriodSummary(
        closed_pnl=closed_pnl,
        open_pnl=open_pnl,
        qqq_return_pct=qqq_return,
        voo_return_pct=voo_return,
        start=effective_start,
        end=effective_end,
    )
    return summary, period_pl_map
