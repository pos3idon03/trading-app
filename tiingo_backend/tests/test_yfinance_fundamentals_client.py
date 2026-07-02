from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd

from features.yfinance.fundamentals_client import fetch_fundamentals_statements


def _make_frame(rows: dict[str, float], ts: datetime) -> pd.DataFrame:
    return pd.DataFrame({ts: rows})


def test_fetch_fundamentals_statements_maps_quarterly_metrics():
    ts = datetime(2024, 3, 31, tzinfo=timezone.utc)
    income = _make_frame(
        {
            "Total Revenue": 100.0,
            "Gross Profit": 40.0,
            "Operating Income": 25.0,
            "Net Income": 20.0,
            "Diluted EPS": 1.5,
            "EBITDA": 30.0,
        },
        ts,
    )
    balance = _make_frame(
        {
            "Total Assets": 500.0,
            "Total Debt": 100.0,
            "Stockholders Equity": 200.0,
            "Total Current Assets": 80.0,
            "Total Current Liabilities": 40.0,
        },
        ts,
    )
    cashflow = _make_frame(
        {"Free Cash Flow": 15.0, "Operating Cash Flow": 18.0},
        ts,
    )
    empty = pd.DataFrame()

    ticker = MagicMock()
    ticker.quarterly_financials = income
    ticker.quarterly_balance_sheet = balance
    ticker.quarterly_cashflow = cashflow
    ticker.financials = empty
    ticker.balance_sheet = empty
    ticker.cashflow = empty

    with patch("features.yfinance.fundamentals_client.yf.Ticker", return_value=ticker):
        rows = fetch_fundamentals_statements("AAPL")

    by_name = {row["metric_name"]: row for row in rows if row["period"] == "2024-Q1"}
    assert by_name["revenue"]["value"] == 100.0
    assert by_name["revenue"]["source"] == "yfinance"
    assert by_name["revenue"]["statement_type"] == "incomeStatement"
    assert by_name["freeCashFlow"]["statement_type"] == "cashFlow"
    assert by_name["totalAssets"]["statement_type"] == "balanceSheet"
    assert by_name["roe"]["value"] == 0.1
    assert by_name["grossMargin"]["value"] == 40.0
    assert by_name["currentRatio"]["value"] == 2.0


def test_fetch_fundamentals_statements_annual_period_label():
    ts = datetime(2023, 12, 31, tzinfo=timezone.utc)
    income = _make_frame({"Total Revenue": 400.0, "Net Income": 50.0}, ts)
    balance = _make_frame({"Total Assets": 1000.0, "Stockholders Equity": 300.0}, ts)
    empty = pd.DataFrame()

    ticker = MagicMock()
    ticker.quarterly_financials = empty
    ticker.quarterly_balance_sheet = empty
    ticker.quarterly_cashflow = empty
    ticker.financials = income
    ticker.balance_sheet = balance
    ticker.cashflow = empty

    with patch("features.yfinance.fundamentals_client.yf.Ticker", return_value=ticker):
        rows = fetch_fundamentals_statements("MSFT")

    annual = [row for row in rows if row["period"] == "FY-2023"]
    assert annual
    assert any(row["metric_name"] == "revenue" for row in annual)


def test_fetch_fundamentals_statements_empty_ticker():
    empty = pd.DataFrame()
    ticker = MagicMock()
    ticker.quarterly_financials = empty
    ticker.quarterly_balance_sheet = empty
    ticker.quarterly_cashflow = empty
    ticker.financials = empty
    ticker.balance_sheet = empty
    ticker.cashflow = empty

    with patch("features.yfinance.fundamentals_client.yf.Ticker", return_value=ticker):
        rows = fetch_fundamentals_statements("UNKNOWN")

    assert rows == []
