"""Tests for financials DAL functions."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_fundamental_row(metric_name: str, value: float, period: str | None = None) -> MagicMock:
    row = MagicMock()
    row.__getitem__ = lambda self, key: {"metric_name": metric_name, "value": value, "period": period}[key]
    return row


class TestGetFundamentals:
    @pytest.mark.asyncio
    async def test_returns_scalar_metrics(self):
        from dal.market_data_dal import get_fundamentals

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {"metric_name": "trailingPE", "value": 28.5, "fetched_at": datetime(2024, 1, 1, tzinfo=timezone.utc)},
            {"metric_name": "trailingEps", "value": 6.13, "fetched_at": datetime(2024, 1, 1, tzinfo=timezone.utc)},
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        rows = await get_fundamentals(mock_session, asset_id=1)

        assert len(rows) == 2
        assert rows[0]["metric_name"] == "trailingPE"
        assert rows[1]["value"] == 6.13

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_data(self):
        from dal.market_data_dal import get_fundamentals

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        rows = await get_fundamentals(mock_session, asset_id=99)
        assert rows == []


class TestGetFinancialStatements:
    @pytest.mark.asyncio
    async def test_returns_statement_rows(self):
        from dal.market_data_dal import get_financial_statements

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {"metric_name": "income_stmt.total_revenue", "value": 394000000000.0, "period": "2023-12-31"},
            {"metric_name": "income_stmt.net_income", "value": 97000000000.0, "period": "2023-12-31"},
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        rows = await get_financial_statements(mock_session, asset_id=1, statement_type="income_stmt")

        assert len(rows) == 2
        assert rows[0]["metric_name"] == "income_stmt.total_revenue"

    @pytest.mark.asyncio
    async def test_empty_for_unknown_statement(self):
        from dal.market_data_dal import get_financial_statements

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        rows = await get_financial_statements(mock_session, asset_id=1, statement_type="cashflow")
        assert rows == []


class TestGetCompanyProfile:
    @pytest.mark.asyncio
    async def test_returns_profile(self):
        from dal.market_data_dal import get_company_profile

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_row = MagicMock(
            sector="Technology",
            industry="Consumer Electronics",
            business_summary="Apple designs...",
            website="https://apple.com",
            country="United States",
            employees=150000,
            officers=[{"name": "Tim Cook", "title": "CEO"}],
            source="yfinance",
            fetched_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        mock_result.scalars.return_value.first.return_value = mock_row
        mock_session.execute = AsyncMock(return_value=mock_result)

        profile = await get_company_profile(mock_session, asset_id=1)

        assert profile is not None
        assert profile["sector"] == "Technology"
        assert profile["employees"] == 150000

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self):
        from dal.market_data_dal import get_company_profile

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        profile = await get_company_profile(mock_session, asset_id=99)
        assert profile is None
