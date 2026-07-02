from unittest.mock import AsyncMock, patch

import pytest

from features.ingestion.fundamentals_orchestrator import run_fundamentals_ingest


@pytest.mark.asyncio
async def test_run_fundamentals_ingest_persists_yfinance_rows():
    session = AsyncMock()
    yfinance_row = {
        "time": "2024-03-31T00:00:00+00:00",
        "metric_name": "revenue",
        "value": 100.0,
        "period": "2024-Q1",
        "statement_type": "incomeStatement",
        "source": "yfinance",
        "raw_data": {},
    }

    with (
        patch(
            "features.ingestion.fundamentals_orchestrator.instrument_dal.get_by_symbol",
            new=AsyncMock(return_value={"id": 7, "symbol": "NVDA", "asset_type": "stock"}),
        ),
        patch(
            "features.ingestion.fundamentals_orchestrator.fetch_fundamentals_rows",
            new=AsyncMock(return_value=[yfinance_row]),
        ),
        patch(
            "features.ingestion.fundamentals_orchestrator.fundamentals_dal.delete_fundamentals_for_instrument",
            new=AsyncMock(return_value=0),
        ) as mock_delete,
        patch(
            "features.ingestion.fundamentals_orchestrator.fundamentals_dal.bulk_insert_fundamentals",
            new=AsyncMock(return_value=1),
        ) as mock_insert,
    ):
        result = await run_fundamentals_ingest(session, ["NVDA"])

    assert result["inserted"] == 1
    assert result["skipped"] == []
    mock_delete.assert_awaited_once_with(session, 7)
    inserted_rows = mock_insert.await_args.args[1]
    assert inserted_rows[0]["instrument_id"] == 7
    assert inserted_rows[0]["source"] == "yfinance"


@pytest.mark.asyncio
async def test_run_fundamentals_ingest_skips_when_no_provider_data():
    session = AsyncMock()
    with (
        patch(
            "features.ingestion.fundamentals_orchestrator.instrument_dal.get_by_symbol",
            new=AsyncMock(return_value={"id": 7, "symbol": "NVDA", "asset_type": "stock"}),
        ),
        patch(
            "features.ingestion.fundamentals_orchestrator.fetch_fundamentals_rows",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "features.ingestion.fundamentals_orchestrator.fundamentals_dal.delete_fundamentals_for_instrument",
            new=AsyncMock(),
        ) as mock_delete,
    ):
        result = await run_fundamentals_ingest(session, ["NVDA"])

    assert result["inserted"] == 0
    assert result["skipped"] == ["NVDA"]
    mock_delete.assert_not_awaited()
