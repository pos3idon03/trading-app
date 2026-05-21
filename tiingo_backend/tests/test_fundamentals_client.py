from datetime import datetime, timezone

from features.tiingo.fundamentals_client import (
    encode_calendar_period,
    encode_fundamental_period,
    flatten_fundamentals_statements,
)


def test_encode_calendar_period():
    assert encode_calendar_period(datetime(2026, 3, 28, tzinfo=timezone.utc)) == "2026-Q1"
    assert encode_calendar_period(datetime(2026, 6, 30, tzinfo=timezone.utc)) == "2026-Q2"
    assert encode_calendar_period(datetime(2025, 12, 27, tzinfo=timezone.utc)) == "2025-Q4"


def test_encode_fiscal_annual_period():
    assert encode_fundamental_period(2024, 0) == "FY-2024"


def test_flatten_uses_calendar_not_tiingo_fiscal_quarter():
    """Apple fiscal Q2 (Jan–Mar) reported 2026-03-28 → calendar 2026-Q1."""
    data = [
        {
            "date": "2026-03-28",
            "year": 2026,
            "quarter": 2,
            "statementData": {
                "incomeStatement": [
                    {"dataCode": "revenue", "value": 111184000000.0},
                    {"dataCode": "eps", "value": 2.02},
                ],
            },
        },
    ]
    rows = flatten_fundamentals_statements(data)
    assert all(r["period"] == "2026-Q1" for r in rows)


def test_flatten_statement_data_nested():
    data = [
        {
            "date": "2025-06-28",
            "year": 2025,
            "quarter": 3,
            "statementData": {
                "incomeStatement": [{"dataCode": "revenue", "value": 100.0}],
                "overview": [{"dataCode": "roe", "value": 1.47}],
            },
        },
    ]
    rows = flatten_fundamentals_statements(data)
    assert len(rows) == 2
    assert all(r["period"] == "2025-Q2" for r in rows)


def test_flatten_legacy_top_level():
    data = [
        {
            "date": "2024-03-31",
            "fiscalYear": 2024,
            "fiscalQuarter": 1,
            "statementType": "incomeStatement",
            "totalRevenue": 100.0,
        },
    ]
    rows = flatten_fundamentals_statements(data)
    assert len(rows) == 1
    assert rows[0]["metric_name"] == "totalRevenue"
    assert rows[0]["period"] == "2024-Q1"


def test_flatten_skips_year_quarter_as_metrics():
    data = [
        {
            "date": "2026-03-28",
            "year": 2026,
            "quarter": 2,
            "statementData": {"overview": [{"dataCode": "roe", "value": 1.0}]},
        },
    ]
    rows = flatten_fundamentals_statements(data)
    assert "year" not in {r["metric_name"] for r in rows}
    assert "quarter" not in {r["metric_name"] for r in rows}
