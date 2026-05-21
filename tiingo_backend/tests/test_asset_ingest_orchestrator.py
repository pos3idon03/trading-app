from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from features.ingestion.asset_ingest_orchestrator import run_asset_full_ingest


@pytest.mark.asyncio
async def test_run_asset_full_ingest_updates_progress():
    session = AsyncMock()
    job_id = uuid4()

    with patch(
        "features.ingestion.asset_ingest_orchestrator.run_ohlcv_backfill",
        new=AsyncMock(return_value=[{"symbol": "AAPL", "status": "ok"}]),
    ), patch(
        "features.ingestion.asset_ingest_orchestrator.run_fundamentals_ingest",
        new=AsyncMock(return_value={"inserted": 1, "skipped": [], "errors": []}),
    ), patch(
        "features.ingestion.asset_ingest_orchestrator.run_news_ingest",
        new=AsyncMock(return_value={"fetched": 2, "inserted": 2, "symbols": ["AAPL"]}),
    ), patch(
        "features.ingestion.asset_ingest_orchestrator.job_dal.update_job_progress",
        new=AsyncMock(),
    ) as mock_progress:
        result = await run_asset_full_ingest(session, "AAPL", job_id=job_id)

    assert result["symbol"] == "AAPL"
    assert "ohlcv" in result
    assert mock_progress.await_count >= 3
