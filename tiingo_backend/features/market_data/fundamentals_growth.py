import re
from dataclasses import dataclass

_QUARTER_RE = re.compile(r"^(\d{4})-Q([1-4])$")


@dataclass(frozen=True)
class MetricGrowth:
    latest_period: str | None
    yoy: float | None
    qoq: float | None
    cagr: float | None


def _pct_change(current: float, reference: float) -> float | None:
    if reference == 0:
        return None
    return round(((current - reference) / reference) * 100.0, 2)


def _parse_period(period: str) -> tuple[int, int] | None:
    match = _QUARTER_RE.match(period)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _prior_quarter(year: int, quarter: int) -> tuple[int, int]:
    if quarter == 1:
        return year - 1, 4
    return year, quarter - 1


def _period_key(year: int, quarter: int) -> str:
    return f"{year}-Q{quarter}"


def _unique_quarterly_values(rows: list[dict]) -> dict[str, float]:
    by_period: dict[str, float] = {}
    for row in rows:
        period = row.get("period") or ""
        if period and period not in by_period:
            by_period[period] = row["value"]
    return by_period


def _newest_quarters(by_period: dict[str, float], count: int = 4) -> list[str]:
    return sorted(by_period.keys(), reverse=True)[:count]


def _growth_for_period(by_period: dict[str, float], period: str) -> tuple[float | None, float | None]:
    parsed = _parse_period(period)
    if not parsed:
        return None, None
    year, quarter = parsed
    current = by_period[period]

    prior_yoy_key = _period_key(year - 1, quarter)
    prior_yoy = by_period.get(prior_yoy_key)
    yoy = _pct_change(current, prior_yoy) if prior_yoy is not None else None

    pq_year, pq_quarter = _prior_quarter(year, quarter)
    prior_qoq_key = _period_key(pq_year, pq_quarter)
    prior_qoq = by_period.get(prior_qoq_key)
    qoq = _pct_change(current, prior_qoq) if prior_qoq is not None else None
    return yoy, qoq


def _compute_cagr(newest: float, oldest: float) -> float | None:
    if oldest <= 0 or newest <= 0:
        return None
    return round(((newest / oldest) ** (4 / 3) - 1) * 100.0, 2)


def compute_metric_growth(rows: list[dict]) -> MetricGrowth:
    by_period = _unique_quarterly_values(rows)
    quarters = _newest_quarters(by_period)
    if not quarters:
        return MetricGrowth(latest_period=None, yoy=None, qoq=None, cagr=None)

    latest_period = quarters[0]
    yoy, qoq = _growth_for_period(by_period, latest_period)

    cagr: float | None = None
    if len(quarters) >= 4:
        newest = by_period[quarters[0]]
        oldest = by_period[quarters[3]]
        cagr = _compute_cagr(newest, oldest)

    return MetricGrowth(
        latest_period=latest_period,
        yoy=yoy,
        qoq=qoq,
        cagr=cagr,
    )


def compute_quarterly_growth(rows: list[dict]) -> MetricGrowth:
    """Backward-compatible alias for compute_metric_growth."""
    return compute_metric_growth(rows)
