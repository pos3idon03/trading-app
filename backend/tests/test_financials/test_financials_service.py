"""Tests for the financials ingestion service."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dtos.market_data_dto import FundamentalRecord


def _make_fundamental_record(metric: str, value: float) -> FundamentalRecord:
    return FundamentalRecord(
        time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        asset_id=1,
        metric_name=metric,
        value=value,
        source="yfinance",
    )


class TestIngestFinancialsForSymbol:
    @pytest.mark.asyncio
    async def test_inserts_fundamentals_and_profile(self):
        from features.data_ingestion.financials_service import ingest_financials_for_symbol

        mock_provider = MagicMock()
        mock_provider.name = "yfinance"
        mock_provider.fetch_fundamentals = AsyncMock(return_value=[
            _make_fundamental_record("trailingPE", 28.5),
        ])
        mock_provider.fetch_financial_statements = AsyncMock(return_value=[
            _make_fundamental_record("income_stmt.total_revenue", 394e9),
        ])
        mock_provider.fetch_company_profile = AsyncMock(return_value={
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "business_summary": "Apple Inc.",
            "website": None, "country": None, "employees": None, "officers": [],
        })

        mock_session = AsyncMock()
        with (
            patch("features.data_ingestion.financials_service.get_provider", return_value=mock_provider),
            patch("features.data_ingestion.financials_service.upsert_asset", new=AsyncMock(return_value=1)),
            patch("features.data_ingestion.financials_service.bulk_insert_fundamentals", new=AsyncMock(return_value=2)),
            patch("features.data_ingestion.financials_service.upsert_company_profile", new=AsyncMock()),
        ):
            result = await ingest_financials_for_symbol(mock_session, "AAPL")

        assert result["symbol"] == "AAPL"
        assert result["fundamentals_inserted"] == 2
        assert result["profile_updated"] is True

    @pytest.mark.asyncio
    async def test_profile_not_updated_when_empty(self):
        from features.data_ingestion.financials_service import ingest_financials_for_symbol

        mock_provider = MagicMock()
        mock_provider.name = "yfinance"
        mock_provider.fetch_fundamentals = AsyncMock(return_value=[])
        mock_provider.fetch_financial_statements = AsyncMock(return_value=[])
        mock_provider.fetch_company_profile = AsyncMock(return_value={
            "sector": None, "industry": None, "business_summary": None,
            "website": None, "country": None, "employees": None, "officers": [],
        })

        mock_session = AsyncMock()
        with (
            patch("features.data_ingestion.financials_service.get_provider", return_value=mock_provider),
            patch("features.data_ingestion.financials_service.upsert_asset", new=AsyncMock(return_value=1)),
            patch("features.data_ingestion.financials_service.bulk_insert_fundamentals", new=AsyncMock(return_value=0)),
            patch("features.data_ingestion.financials_service.upsert_company_profile", new=AsyncMock()) as mock_upsert,
        ):
            result = await ingest_financials_for_symbol(mock_session, "AAPL")

        assert result["profile_updated"] is False
        mock_upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_symbol_is_uppercased(self):
        from features.data_ingestion.financials_service import ingest_financials_for_symbol

        mock_provider = MagicMock()
        mock_provider.name = "yfinance"
        mock_provider.fetch_fundamentals = AsyncMock(return_value=[])
        mock_provider.fetch_financial_statements = AsyncMock(return_value=[])
        mock_provider.fetch_company_profile = AsyncMock(return_value={})

        captured = {}
        async def mock_upsert_asset(session, symbol, **kwargs):
            captured["symbol"] = symbol
            return 1

        mock_session = AsyncMock()
        with (
            patch("features.data_ingestion.financials_service.get_provider", return_value=mock_provider),
            patch("features.data_ingestion.financials_service.upsert_asset", new=mock_upsert_asset),
            patch("features.data_ingestion.financials_service.bulk_insert_fundamentals", new=AsyncMock(return_value=0)),
        ):
            await ingest_financials_for_symbol(mock_session, "aapl")

        assert captured["symbol"] == "AAPL"


class TestYFinanceStatementConversion:
    def test_df_to_fundamental_records_basic(self):
        import pandas as pd
        from features.data_ingestion.yfinance_provider import _df_to_fundamental_records

        dates = pd.to_datetime(["2023-12-31", "2022-12-31"])
        df = pd.DataFrame(
            {"Total Revenue": [394e9, 383e9], "Net Income": [97e9, 100e9]},
            index=dates,
        ).T
        df.columns = pd.DatetimeIndex(["2023-12-31", "2022-12-31"])

        records = _df_to_fundamental_records(df, "income_stmt", asset_id=1, source="yfinance")

        assert len(records) == 4
        names = {r.metric_name for r in records}
        assert "income_stmt.total_revenue" in names
        assert "income_stmt.net_income" in names

    def test_df_to_fundamental_records_skips_nan(self):
        import math
        import pandas as pd
        from features.data_ingestion.yfinance_provider import _df_to_fundamental_records

        import numpy as np
        dates = pd.DatetimeIndex(["2023-12-31"])
        df = pd.DataFrame({"Total Revenue": [float("nan")]}, index=dates).T
        df.columns = dates

        records = _df_to_fundamental_records(df, "income_stmt", asset_id=1, source="yfinance")
        assert records == []

    def test_df_to_fundamental_records_empty_df(self):
        import pandas as pd
        from features.data_ingestion.yfinance_provider import _df_to_fundamental_records

        records = _df_to_fundamental_records(pd.DataFrame(), "income_stmt", asset_id=1, source="yfinance")
        assert records == []
