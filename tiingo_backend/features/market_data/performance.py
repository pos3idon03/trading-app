import calendar
from datetime import date, datetime, timedelta

PERFORMANCE_PERIODS = ("1W", "1M", "3M", "6M", "YTD", "1Y", "2Y", "5Y")
EXAMPLE_INVESTMENT = 100.0


def _bar_date(bar: dict) -> date:
    t = bar["time"]
    return t.date() if isinstance(t, datetime) else t


def _shift_months(d: date, months: int) -> date:
    month = d.month - months
    year = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, max_day))


def _reference_date(as_of: date, period: str) -> date:
    if period == "1W":
        return as_of - timedelta(days=7)
    if period == "1M":
        return _shift_months(as_of, 1)
    if period == "3M":
        return _shift_months(as_of, 3)
    if period == "6M":
        return _shift_months(as_of, 6)
    if period == "YTD":
        return date(as_of.year, 1, 1)
    if period == "1Y":
        return as_of - timedelta(days=365)
    if period == "2Y":
        return as_of - timedelta(days=365 * 2)
    if period == "5Y":
        return as_of - timedelta(days=365 * 5)
    raise ValueError(f"Unknown period: {period}")


def _close_on_or_before(bars: list[dict], target: date) -> float | None:
    ref_close: float | None = None
    for bar in bars:
        if _bar_date(bar) <= target:
            ref_close = bar["close"]
        else:
            break
    return ref_close


def _pct_change(current: float, reference: float) -> float:
    if reference == 0:
        return 0.0
    return ((current - reference) / reference) * 100.0


def _dividends_after(bars: list[dict], ref_date: date, as_of: date) -> float:
    total = 0.0
    for bar in bars:
        bar_date = _bar_date(bar)
        if ref_date < bar_date <= as_of:
            total += float(bar.get("div_cash") or 0)
    return total


def _empty_period(period: str) -> dict:
    return {
        "period": period,
        "price_change_pct": None,
        "dividend_return_pct": None,
        "total_return_pct": None,
        "change_pct": None,
        "example_investment": EXAMPLE_INVESTMENT,
        "example_outcome": None,
        "example_dividend_income": None,
    }


def _period_breakdown(sorted_bars: list[dict], period: str) -> dict | None:
    as_of = _bar_date(sorted_bars[-1])
    latest_close = sorted_bars[-1]["close"]
    ref_date = _reference_date(as_of, period)
    ref_close = _close_on_or_before(sorted_bars, ref_date)
    if ref_close is None:
        return None

    price_pct = round(_pct_change(latest_close, ref_close), 2)
    div_sum = _dividends_after(sorted_bars, ref_date, as_of)
    div_pct = round((div_sum / ref_close) * 100.0, 2)
    total_pct = round(price_pct + div_pct, 2)
    example_income = round(EXAMPLE_INVESTMENT * div_pct / 100.0, 2)
    example_outcome = round(EXAMPLE_INVESTMENT * (1 + total_pct / 100.0), 2)

    return {
        "period": period,
        "price_change_pct": price_pct,
        "dividend_return_pct": div_pct,
        "total_return_pct": total_pct,
        "change_pct": total_pct,
        "example_investment": EXAMPLE_INVESTMENT,
        "example_outcome": example_outcome,
        "example_dividend_income": example_income,
    }


def compute_performance_breakdown(bars: list[dict]) -> list[dict]:
    if not bars:
        return [_empty_period(p) for p in PERFORMANCE_PERIODS]

    sorted_bars = sorted(bars, key=lambda b: b["time"])
    rows: list[dict] = []
    for period in PERFORMANCE_PERIODS:
        row = _period_breakdown(sorted_bars, period)
        rows.append(row if row is not None else _empty_period(period))
    return rows


def compute_performance(bars: list[dict]) -> dict[str, float | None]:
    return {r["period"]: r["total_return_pct"] for r in compute_performance_breakdown(bars)}
