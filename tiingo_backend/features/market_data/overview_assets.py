from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dal import fundamentals_dal, instrument_dal, ohlcv_dal
from features.market_data.fundamentals_growth import MetricGrowth, compute_metric_growth
from features.market_data.performance import compute_performance_breakdown
from features.market_data.performance_service import _PERFORMANCE_LOOKBACK_DAYS
from features.market_data.stock_kpis import load_stock_kpis

_OVERVIEW_PERFORMANCE_PERIODS = ("1W", "1M", "3M", "6M", "YTD", "1Y", "2Y", "5Y")

def _kpi_value(kpis: list, key: str) -> float | None:
    for item in kpis:
        if item.key == key:
            return item.value
    return None


def _growth_dict(growth: MetricGrowth) -> dict:
    return {
        "latest_period": growth.latest_period,
        "yoy": growth.yoy,
        "qoq": growth.qoq,
        "cagr": growth.cagr,
    }


def _period_map(bars: list[dict]) -> dict[str, float | None]:
    breakdown = compute_performance_breakdown(bars)
    return {
        row["period"]: row.get("price_change_pct")
        for row in breakdown
        if row["period"] in _OVERVIEW_PERFORMANCE_PERIODS
    }


async def _load_bars(session: AsyncSession, instrument_id: int) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=_PERFORMANCE_LOOKBACK_DAYS)
    bars, _ = await ohlcv_dal.get_bars(
        session,
        instrument_id,
        "1d",
        start=start,
        end=end,
        limit=_PERFORMANCE_LOOKBACK_DAYS,
    )
    return bars


async def _load_metric_growth(
    session: AsyncSession,
    instrument_id: int,
    metric_name: str,
) -> dict:
    rows = await fundamentals_dal.list_fundamentals_for_symbol(
        session,
        instrument_id,
        period_type="quarterly",
        metric_names=[metric_name],
        order="desc",
        limit=40,
    )
    return _growth_dict(compute_metric_growth(rows))


async def _build_stock_row(session: AsyncSession, instrument: dict) -> dict:
    _, as_of, kpis = await load_stock_kpis(session, instrument["id"])
    bars = await _load_bars(session, instrument["id"])
    perf = _period_map(bars)

    revenue = await _load_metric_growth(session, instrument["id"], "revenue")
    ebitda = await _load_metric_growth(session, instrument["id"], "ebitda")
    ocf = await _load_metric_growth(session, instrument["id"], "ncfo")

    return {
        "symbol": instrument["symbol"],
        "name": instrument.get("name"),
        "as_of": as_of,
        "pe_ratio": _kpi_value(kpis, "pe_ratio"),
        "dividend_yield": _kpi_value(kpis, "dividend_yield"),
        "debt_equity": _kpi_value(kpis, "debtEquity"),
        "current_ratio": _kpi_value(kpis, "currentRatio"),
        "eps_ttm": _kpi_value(kpis, "eps_ttm"),
        "revenue_growth": revenue,
        "ebitda_growth": ebitda,
        "ocf_growth": ocf,
        "price_change_6m": perf.get("6M"),
    }


async def _build_price_row(session: AsyncSession, instrument: dict) -> dict:
    bars = await _load_bars(session, instrument["id"])
    if not bars:
        return {
            "symbol": instrument["symbol"],
            "name": instrument.get("name"),
            "as_of": None,
            "dividend_yield": None,
            "performance": {p: None for p in _OVERVIEW_PERFORMANCE_PERIODS},
        }

    as_of = bars[-1]["time"]
    perf = _period_map(bars)
    _, _, kpis = await load_stock_kpis(session, instrument["id"])
    div_yield = _kpi_value(kpis, "dividend_yield")
    if div_yield is not None and div_yield == 0:
        div_yield = None

    return {
        "symbol": instrument["symbol"],
        "name": instrument.get("name"),
        "as_of": as_of,
        "dividend_yield": div_yield,
        "performance": perf,
    }


async def load_asset_overview(
    session: AsyncSession,
    asset_type: str,
) -> dict:
    instruments = [
        inst
        for inst in await instrument_dal.list_instruments(session, active_only=True)
        if inst["asset_type"] == asset_type
    ]

    rows: list[dict] = []
    as_of: datetime | None = None
    for instrument in instruments:
        if asset_type == "stock":
            row = await _build_stock_row(session, instrument)
        else:
            row = await _build_price_row(session, instrument)
        row_as_of = row.get("as_of")
        if row_as_of is not None and (as_of is None or row_as_of > as_of):
            as_of = row_as_of
        rows.append(row)

    return {"asset_type": asset_type, "as_of": as_of, "rows": rows}
