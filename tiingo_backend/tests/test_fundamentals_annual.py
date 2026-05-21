from datetime import datetime, timezone

from features.market_data.fundamentals_annual import aggregate_quarterly_to_annual

_T = datetime(2024, 9, 30, tzinfo=timezone.utc)


def _row(period: str, metric: str, value: float, time: datetime = _T) -> dict:
    return {
        "time": time,
        "metric_name": metric,
        "value": value,
        "period": period,
        "statement_type": "incomeStatement",
    }


def test_sums_flow_metrics_by_fiscal_year():
    rows = [
        _row("2024-Q1", "revenue", 100.0),
        _row("2024-Q2", "revenue", 110.0),
        _row("2024-Q3", "revenue", 120.0),
        _row("2024-Q4", "revenue", 130.0),
    ]
    annual = aggregate_quarterly_to_annual(rows)
    assert len(annual) == 1
    assert annual[0]["period"] == "FY-2024"
    assert annual[0]["value"] == 460.0


def test_balance_sheet_uses_q4():
    rows = [
        _row("2024-Q1", "totalAssets", 100.0),
        _row("2024-Q4", "totalAssets", 150.0),
    ]
    annual = aggregate_quarterly_to_annual(rows)
    assert annual[0]["value"] == 150.0


def test_eps_uses_q4_not_sum():
    rows = [
        _row("2024-Q1", "eps", 1.0),
        _row("2024-Q2", "eps", 1.1),
        _row("2024-Q4", "eps", 2.5),
    ]
    annual = aggregate_quarterly_to_annual(rows)
    assert annual[0]["value"] == 2.5
