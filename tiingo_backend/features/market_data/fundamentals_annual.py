"""Build annual fundamentals series from quarterly rows when Tiingo has no FY statements."""

import re
from collections import defaultdict

_QUARTERLY_PERIOD_RE = re.compile(r"^(\d{4})-Q([1-4])$")

# Flow metrics: sum quarters within the fiscal year.
_SUM_METRICS = frozenset({
    "revenue",
    "grossProfit",
    "opinc",
    "netinc",
    "ebitda",
    "freeCashFlow",
    "ncfo",
})


def _fiscal_year_from_period(period: str | None) -> str | None:
    if not period:
        return None
    if period.startswith("FY-"):
        return period[3:]
    match = _QUARTERLY_PERIOD_RE.match(period)
    return match.group(1) if match else None


def _pick_year_end_point(points: list[dict]) -> dict:
    by_q = {int(_QUARTERLY_PERIOD_RE.match(p["period"]).group(2)): p for p in points
            if p.get("period") and _QUARTERLY_PERIOD_RE.match(p["period"])}
    if 4 in by_q:
        return by_q[4]
    return max(points, key=lambda p: p["time"])


def aggregate_quarterly_to_annual(quarterly_rows: list[dict]) -> list[dict]:
    """Roll up quarterly statement rows into FY-YYYY annual points."""
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in quarterly_rows:
        year = _fiscal_year_from_period(row.get("period"))
        if not year:
            continue
        buckets[(row["metric_name"], year)].append(row)

    annual: list[dict] = []
    for (metric_name, year), points in buckets.items():
        points.sort(key=lambda p: p["time"])
        if metric_name in _SUM_METRICS:
            value = sum(p["value"] for p in points)
            anchor = points[-1]
        else:
            anchor = _pick_year_end_point(points)
            value = anchor["value"]

        annual.append({
            "time": anchor["time"],
            "metric_name": metric_name,
            "value": value,
            "period": f"FY-{year}",
            "statement_type": anchor.get("statement_type"),
        })

    return annual
