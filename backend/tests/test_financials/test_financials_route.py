"""Tests for the financials API routes."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


_ASSET_ID = 1
_SYMBOL = "AAPL"
_NOW = datetime(2024, 6, 1, tzinfo=timezone.utc)


def _mock_session():
    return AsyncMock()


class TestGetOverview:
    @pytest.mark.asyncio
    async def test_returns_metrics_when_data_exists(self):
        from routes.financials import get_overview

        mock_session = _mock_session()
        rows = [
            {"metric_name": "trailingPE", "value": 28.5, "fetched_at": _NOW},
            {"metric_name": "trailingEps", "value": 6.13, "fetched_at": _NOW},
        ]
        with (
            patch("routes.financials.get_asset_id_by_symbol", new=AsyncMock(return_value=_ASSET_ID)),
            patch("routes.financials.get_fundamentals", new=AsyncMock(return_value=rows)),
        ):
            resp = await get_overview(_SYMBOL, session=mock_session)

        assert resp.symbol == _SYMBOL
        assert resp.metrics["trailingPE"] == 28.5
        assert resp.metrics["trailingEps"] == 6.13

    @pytest.mark.asyncio
    async def test_raises_404_when_no_data(self):
        from fastapi import HTTPException
        from routes.financials import get_overview

        with (
            patch("routes.financials.get_asset_id_by_symbol", new=AsyncMock(return_value=_ASSET_ID)),
            patch("routes.financials.get_fundamentals", new=AsyncMock(return_value=[])),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_overview(_SYMBOL, session=_mock_session())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_when_asset_missing(self):
        from fastapi import HTTPException
        from routes.financials import get_overview

        with patch("routes.financials.get_asset_id_by_symbol", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc_info:
                await get_overview("UNKNOWN", session=_mock_session())

        assert exc_info.value.status_code == 404


class TestGetIncomeStatement:
    @pytest.mark.asyncio
    async def test_pivots_rows_correctly(self):
        from routes.financials import get_income_statement

        rows = [
            {"metric_name": "income_stmt.total_revenue", "value": 394e9, "period": "2023-12-31"},
            {"metric_name": "income_stmt.total_revenue", "value": 383e9, "period": "2022-12-31"},
            {"metric_name": "income_stmt.net_income", "value": 97e9, "period": "2023-12-31"},
        ]
        with (
            patch("routes.financials.get_asset_id_by_symbol", new=AsyncMock(return_value=_ASSET_ID)),
            patch("routes.financials.get_financial_statements", new=AsyncMock(return_value=rows)),
        ):
            resp = await get_income_statement(_SYMBOL, session=_mock_session())

        assert resp.statement_type == "income_stmt"
        assert "2023-12-31" in resp.periods
        assert "2022-12-31" in resp.periods
        metrics = {r.metric: r.values for r in resp.rows}
        assert "total_revenue" in metrics
        assert metrics["total_revenue"]["2023-12-31"] == 394e9

    @pytest.mark.asyncio
    async def test_returns_empty_rows_when_no_statements(self):
        from routes.financials import get_income_statement

        with (
            patch("routes.financials.get_asset_id_by_symbol", new=AsyncMock(return_value=_ASSET_ID)),
            patch("routes.financials.get_financial_statements", new=AsyncMock(return_value=[])),
        ):
            resp = await get_income_statement(_SYMBOL, session=_mock_session())

        assert resp.rows == []
        assert resp.periods == []


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_returns_profile(self):
        from routes.financials import get_profile

        profile_data = {
            "sector": "Technology", "industry": "Consumer Electronics",
            "business_summary": "Apple Inc. designs...", "website": "https://apple.com",
            "country": "United States", "employees": 150000,
            "officers": [{"name": "Tim Cook", "title": "CEO"}],
            "fetched_at": _NOW,
        }
        with (
            patch("routes.financials.get_asset_id_by_symbol", new=AsyncMock(return_value=_ASSET_ID)),
            patch("routes.financials.get_company_profile", new=AsyncMock(return_value=profile_data)),
        ):
            resp = await get_profile(_SYMBOL, session=_mock_session())

        assert resp.sector == "Technology"
        assert resp.employees == 150000

    @pytest.mark.asyncio
    async def test_raises_404_when_no_profile(self):
        from fastapi import HTTPException
        from routes.financials import get_profile

        with (
            patch("routes.financials.get_asset_id_by_symbol", new=AsyncMock(return_value=_ASSET_ID)),
            patch("routes.financials.get_company_profile", new=AsyncMock(return_value=None)),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_profile(_SYMBOL, session=_mock_session())

        assert exc_info.value.status_code == 404


class TestIngestFinancials:
    @pytest.mark.asyncio
    async def test_returns_completed_status(self):
        from routes.financials import ingest_financials

        ingest_result = {"symbol": _SYMBOL, "fundamentals_inserted": 42, "profile_updated": True}
        with patch(
            "routes.financials.ingest_financials_for_symbol",
            new=AsyncMock(return_value=ingest_result),
        ):
            resp = await ingest_financials(_SYMBOL, session=_mock_session())

        assert resp.status == "completed"
        assert resp.fundamentals_inserted == 42
        assert resp.profile_updated is True

    @pytest.mark.asyncio
    async def test_raises_500_on_provider_error(self):
        from fastapi import HTTPException
        from routes.financials import ingest_financials

        with patch(
            "routes.financials.ingest_financials_for_symbol",
            new=AsyncMock(side_effect=RuntimeError("yfinance timeout")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await ingest_financials(_SYMBOL, session=_mock_session())

        assert exc_info.value.status_code == 500
