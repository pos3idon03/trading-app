from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

from features.tiingo.fundamentals_client import encode_calendar_period, encode_fundamental_period
from utils.logging import get_logger

logger = get_logger(__name__)

_INCOME_METRICS: dict[str, tuple[str, ...]] = {
    "revenue": ("Total Revenue", "Revenue"),
    "grossProfit": ("Gross Profit",),
    "opinc": ("Operating Income",),
    "netinc": ("Net Income", "Net Income Common Stockholders"),
    "eps": ("Diluted EPS", "Basic EPS"),
    "ebitda": ("EBITDA", "Normalized EBITDA"),
}

_CASHFLOW_METRICS: dict[str, tuple[str, ...]] = {
    "freeCashFlow": ("Free Cash Flow",),
    "ncfo": ("Operating Cash Flow", "Total Cash From Operating Activities"),
}

_BALANCE_METRICS: dict[str, tuple[str, ...]] = {
    "totalAssets": ("Total Assets",),
    "debt": ("Total Debt", "Long Term Debt And Capital Lease Obligation"),
    "equity": (
        "Stockholders Equity",
        "Total Equity Gross Minority Interest",
        "Common Stock Equity",
    ),
    "currentAssets": ("Total Current Assets", "Current Assets"),
    "currentLiabilities": ("Total Current Liabilities", "Current Liabilities"),
}


def _lookup_value(frame: pd.DataFrame | None, aliases: tuple[str, ...]) -> float | None:
    if frame is None or frame.empty:
        return None
    for alias in aliases:
        if alias in frame.index:
            val = frame.loc[alias]
            if isinstance(val, pd.Series):
                val = val.iloc[0] if len(val) else None
            if val is not None and pd.notna(val):
                return float(val)
    return None


def _column_timestamp(col) -> datetime:
    if isinstance(col, datetime):
        ts = col
    elif hasattr(col, "to_pydatetime"):
        ts = col.to_pydatetime()
    else:
        ts = datetime.fromisoformat(str(col)[:10])
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _period_label(ts: datetime, *, annual: bool) -> str:
    if annual:
        return encode_fundamental_period(ts.year, 0)
    return encode_calendar_period(ts)


def _append_row(
    rows: list[dict],
    *,
    ts: datetime,
    metric_name: str,
    value: float,
    period: str,
    statement_type: str,
) -> None:
    rows.append({
        "time": ts,
        "metric_name": metric_name,
        "value": value,
        "period": period,
        "statement_type": statement_type,
        "source": "yfinance",
        "raw_data": {"provider": "yfinance", "period": period},
    })


def _extract_statement_metrics(
    rows: list[dict],
    frame: pd.DataFrame | None,
    metric_map: dict[str, tuple[str, ...]],
    statement_type: str,
    *,
    annual: bool,
) -> None:
    if frame is None or frame.empty:
        return
    for col in frame.columns:
        ts = _column_timestamp(col)
        period = _period_label(ts, annual=annual)
        col_frame = frame[[col]]
        for code, aliases in metric_map.items():
            val = _lookup_value(col_frame, aliases)
            if val is not None:
                _append_row(
                    rows,
                    ts=ts,
                    metric_name=code,
                    value=val,
                    period=period,
                    statement_type=statement_type,
                )


def _period_values(rows: list[dict], period: str) -> dict[str, float]:
    return {
        row["metric_name"]: row["value"]
        for row in rows
        if row.get("period") == period and row.get("statement_type") != "overview"
    }


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _append_overview_metrics(rows: list[dict], period: str, values: dict[str, float]) -> None:
    ts = next((r["time"] for r in rows if r.get("period") == period), None)
    if ts is None:
        return
    revenue = values.get("revenue")
    gross = values.get("grossProfit")
    netinc = values.get("netinc")
    assets = values.get("totalAssets")
    debt = values.get("debt")
    equity = values.get("equity")
    current_assets = values.get("currentAssets")
    current_liab = values.get("currentLiabilities")

    overview: dict[str, float | None] = {
        "roe": _safe_ratio(netinc, equity),
        "roa": _safe_ratio(netinc, assets),
        "debtEquity": _safe_ratio(debt, equity),
        "grossMargin": (gross / revenue * 100.0) if gross is not None and revenue else None,
        "profitMargin": (netinc / revenue * 100.0) if netinc is not None and revenue else None,
        "currentRatio": _safe_ratio(current_assets, current_liab),
    }
    for code, val in overview.items():
        if val is not None:
            _append_row(
                rows,
                ts=ts,
                metric_name=code,
                value=val,
                period=period,
                statement_type="overview",
            )


def _add_overview_for_periods(rows: list[dict]) -> None:
    periods = {row["period"] for row in rows if row.get("period")}
    for period in periods:
        values = _period_values(rows, period)
        _append_overview_metrics(rows, period, values)


def _flatten_frames(
    income: pd.DataFrame | None,
    balance: pd.DataFrame | None,
    cashflow: pd.DataFrame | None,
    *,
    annual: bool,
) -> list[dict]:
    rows: list[dict] = []
    _extract_statement_metrics(rows, income, _INCOME_METRICS, "incomeStatement", annual=annual)
    _extract_statement_metrics(rows, balance, _BALANCE_METRICS, "balanceSheet", annual=annual)
    _extract_statement_metrics(rows, cashflow, _CASHFLOW_METRICS, "cashFlow", annual=annual)
    _add_overview_for_periods(rows)
    return rows


def fetch_fundamentals_statements(symbol: str) -> list[dict]:
    ticker = yf.Ticker(symbol.upper())
    rows: list[dict] = []
    rows.extend(
        _flatten_frames(
            ticker.quarterly_financials,
            ticker.quarterly_balance_sheet,
            ticker.quarterly_cashflow,
            annual=False,
        ),
    )
    rows.extend(
        _flatten_frames(
            ticker.financials,
            ticker.balance_sheet,
            ticker.cashflow,
            annual=True,
        ),
    )
    logger.info("yfinance_fundamentals_fetched", symbol=symbol, metrics=len(rows))
    return rows
