from datetime import datetime, timezone

import pytest

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


def test_flatten_uses_fiscal_period_when_available():
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
    assert all(r["period"] == "2026-Q2" for r in rows)
    assert all(r["raw_data"]["as_reported"] is True for r in rows)


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
    assert all(r["period"] == "2025-Q3" for r in rows)


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


@pytest.mark.asyncio
async def test_fetch_fundamentals_statements_requests_as_reported():
    from unittest.mock import AsyncMock, patch

    from features.tiingo import fundamentals_client

    response = AsyncMock()
    response.raise_for_status = lambda: None
    response.json = lambda: []

    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    with patch("features.tiingo.fundamentals_client.get_token", return_value="token"), patch(
        "features.tiingo.fundamentals_client.httpx.AsyncClient",
        return_value=client,
    ):
        await fundamentals_client.fetch_fundamentals_statements("AAPL", as_reported=True)

    assert client.get.await_args.kwargs["params"]["asReported"] == "true"
