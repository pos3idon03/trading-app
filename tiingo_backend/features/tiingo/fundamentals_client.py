from datetime import datetime, timezone

import httpx

from features.tiingo.common import get_token
from utils.logging import get_logger

logger = get_logger(__name__)

_FUND_URL = "https://api.tiingo.com/tiingo/fundamentals"

_SKIP_KEYS = frozenset({
    "date",
    "reportDate",
    "fiscalYear",
    "fiscalQuarter",
    "year",
    "quarter",
    "statementData",
    "statementType",
})


def encode_calendar_period(report_date: datetime) -> str:
    """Calendar quarter label derived from a statement or filing date.

    When Tiingo asReported=true, report_date is the SEC filing/publication date.
    Period labels prefer Tiingo fiscal year/quarter fields when present in flatten.
    """
    calendar_quarter = (report_date.month - 1) // 3 + 1
    return f"{report_date.year}-Q{calendar_quarter}"


def encode_fundamental_period(fiscal_year: int | str | None, fiscal_quarter: int | str | None) -> str:
    """Map Tiingo fiscal fields (used only for native annual rows with quarter=0)."""
    year = str(fiscal_year or "")
    try:
        quarter = int(fiscal_quarter) if fiscal_quarter is not None else None
    except (TypeError, ValueError):
        quarter = None
    if quarter == 0:
        return f"FY-{year}" if year else "FY-unknown"
    if quarter in (1, 2, 3, 4):
        return f"{year}-Q{quarter}"
    return f"{year}-Q{quarter}" if year else "unknown"


def _append_metric_row(
    rows: list[dict],
    *,
    ts: datetime,
    metric_name: str,
    value: float,
    period: str,
    statement_type: str,
    raw_data: dict,
) -> None:
    rows.append({
        "time": ts,
        "metric_name": metric_name,
        "value": value,
        "period": period,
        "statement_type": statement_type,
        "source": "tiingo",
        "raw_data": raw_data,
    })


def _flatten_statement_data(
    rows: list[dict],
    stmt: dict,
    ts: datetime,
    period: str,
) -> None:
    statement_data = stmt.get("statementData")
    if not isinstance(statement_data, dict):
        return
    for st_type, items in statement_data.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            code = item.get("dataCode")
            val = item.get("value")
            if code and isinstance(val, (int, float)):
                _append_metric_row(
                    rows,
                    ts=ts,
                    metric_name=str(code),
                    value=float(val),
                    period=period,
                    statement_type=str(st_type),
                    raw_data=stmt,
                )


def _flatten_top_level(stmt: dict, ts: datetime, period: str, rows: list[dict]) -> None:
    st_type = stmt.get("statementType", "statements")
    for key, val in stmt.items():
        if key in _SKIP_KEYS:
            continue
        if isinstance(val, (int, float)):
            _append_metric_row(
                rows,
                ts=ts,
                metric_name=key,
                value=float(val),
                period=period,
                statement_type=str(st_type),
                raw_data=stmt,
            )


def _resolve_statement_period(stmt: dict, ts: datetime) -> str:
    year = stmt.get("year") if stmt.get("year") is not None else stmt.get("fiscalYear")
    quarter = stmt.get("quarter") if stmt.get("quarter") is not None else stmt.get("fiscalQuarter")
    if year is not None and quarter is not None:
        return encode_fundamental_period(year, quarter)
    return encode_calendar_period(ts)


def flatten_fundamentals_statements(
    data: list[dict],
    *,
    as_reported: bool = True,
) -> list[dict]:
    rows: list[dict] = []
    for stmt in data:
        report_date = stmt.get("date") or stmt.get("reportDate")
        if not report_date:
            continue
        ts = datetime.fromisoformat(str(report_date)[:10]).replace(tzinfo=timezone.utc)
        period = _resolve_statement_period(stmt, ts)
        stamped = {**stmt, "as_reported": as_reported}
        _flatten_statement_data(rows, stamped, ts, period)
        if not stmt.get("statementData"):
            _flatten_top_level(stamped, ts, period, rows)
    return rows


async def fetch_fundamentals_statements(symbol: str, *, as_reported: bool = True) -> list[dict]:
    token = get_token()
    url = f"{_FUND_URL}/{symbol.upper()}/statements"
    params: dict[str, str] = {"token": token}
    if as_reported:
        params["asReported"] = "true"
    else:
        logger.warning("fundamentals_fetch_not_point_in_time", symbol=symbol)
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        payload = resp.json()

    data = payload if isinstance(payload, list) else payload.get("statements", [])
    rows = flatten_fundamentals_statements(data, as_reported=as_reported)
    logger.info(
        "fundamentals_fetched",
        symbol=symbol,
        metrics=len(rows),
        as_reported=as_reported,
    )
    return rows
