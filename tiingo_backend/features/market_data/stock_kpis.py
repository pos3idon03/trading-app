from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from dal import fundamentals_dal, ohlcv_dal
from features.market_data.dividend_yield import resolve_dividend_yield

KpiFormat = Literal["ratio", "percent", "currency", "perShare"]

_OVERVIEW_METRICS = (
    ("roe", "Return on Equity", "ratio"),
    ("roa", "Return on Assets", "ratio"),
    ("debtEquity", "Debt / Equity", "ratio"),
    ("grossMargin", "Gross Margin", "percent"),
    ("profitMargin", "Profit Margin", "percent"),
    ("currentRatio", "Current Ratio", "ratio"),
)


@dataclass(frozen=True)
class KpiItem:
    key: str
    label: str
    value: float | None
    format: KpiFormat


def _unique_quarterly_eps(rows: list[dict]) -> list[float]:
    seen: set[str] = set()
    values: list[float] = []
    for row in rows:
        period = row.get("period") or ""
        if period in seen:
            continue
        seen.add(period)
        values.append(row["value"])
        if len(values) == 4:
            break
    return values


def _compute_ttm_eps(eps_rows: list[dict]) -> float | None:
    values = _unique_quarterly_eps(eps_rows)
    if len(values) < 4:
        return None
    return sum(values)


def _build_kpi(key: str, label: str, value: float | None, fmt: KpiFormat) -> KpiItem:
    rounded = round(value, 2) if value is not None else None
    return KpiItem(key=key, label=label, value=rounded, format=fmt)


def _valuation_kpis(price: float, ttm_eps: float | None, div_yield: float | None) -> list[KpiItem]:
    pe = price / ttm_eps if ttm_eps and ttm_eps > 0 else None
    return [
        _build_kpi("pe_ratio", "P/E Ratio", pe, "ratio"),
        _build_kpi("dividend_yield", "Dividend Yield", div_yield, "percent"),
        _build_kpi("eps_ttm", "EPS (TTM)", ttm_eps, "perShare"),
    ]


def _overview_kpis(latest: dict[str, float]) -> list[KpiItem]:
    items: list[KpiItem] = []
    for key, label, fmt in _OVERVIEW_METRICS:
        val = latest.get(key)
        items.append(_build_kpi(key, label, val, fmt))
    return items


async def _latest_overview_metrics(
    session: AsyncSession,
    instrument_id: int,
) -> dict[str, float]:
    names = [m[0] for m in _OVERVIEW_METRICS]
    rows = await fundamentals_dal.list_fundamentals_for_symbol(
        session,
        instrument_id,
        period_type="quarterly",
        metric_names=names,
        order="desc",
        limit=200,
    )
    latest: dict[str, float] = {}
    for row in rows:
        name = row["metric_name"]
        if name not in latest:
            latest[name] = row["value"]
    return latest


async def load_stock_kpis(
    session: AsyncSession,
    instrument_id: int,
    *,
    symbol: str | None = None,
    tiingo_ticker: str | None = None,
) -> tuple[float | None, datetime | None, list[KpiItem]]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=400)

    bars, _ = await ohlcv_dal.get_bars(
        session,
        instrument_id,
        "1d",
        source="tiingo_eod",
        start=start,
        end=end,
        limit=400,
    )
    if not bars:
        return None, None, []

    price = bars[-1]["close"]
    as_of = bars[-1]["time"]

    if symbol:
        div_yield = await resolve_dividend_yield(
            session,
            instrument_id,
            symbol=symbol,
            tiingo_ticker=tiingo_ticker,
        )
    else:
        div_start = end - timedelta(days=365)
        div_sum = await ohlcv_dal.sum_div_cash(
            session, instrument_id, start=div_start, end=end,
        )
        div_yield = (div_sum / price * 100.0) if price > 0 else None

    eps_rows = await fundamentals_dal.list_fundamentals_for_symbol(
        session,
        instrument_id,
        period_type="quarterly",
        metric_names=["eps"],
        order="desc",
        limit=20,
    )
    ttm_eps = _compute_ttm_eps(eps_rows)
    overview = await _latest_overview_metrics(session, instrument_id)

    kpis = _valuation_kpis(price, ttm_eps, div_yield)
    kpis.extend(_overview_kpis(overview))
    return price, as_of, kpis
