from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from features.worker.tasks import create_and_enqueue_job, enqueue_ingestion_job


@pytest.mark.asyncio
async def test_enqueue_ingestion_job_commits_and_enqueues():
    session = AsyncMock()
    job_id = uuid4()
    mock_pool = AsyncMock()

    with patch("features.worker.tasks.get_arq_pool", new=AsyncMock(return_value=mock_pool)):
        await enqueue_ingestion_job(session, job_id, "ohlcv_backfill", {"symbols": ["AAPL"]})

    session.commit.assert_awaited_once()
    mock_pool.enqueue_job.assert_awaited_once_with(
        "run_ingestion_job",
        str(job_id),
        "ohlcv_backfill",
        {"symbols": ["AAPL"]},
    )


@pytest.mark.asyncio
async def test_create_and_enqueue_job():
    session = AsyncMock()
    job_id = uuid4()
    mock_job = {"id": job_id, "job_type": "asset_full_ingest", "status": "pending"}

    with patch(
        "features.worker.tasks.job_dal.create_job",
        new=AsyncMock(return_value=mock_job),
    ), patch(
        "features.worker.tasks.enqueue_ingestion_job",
        new=AsyncMock(),
    ) as mock_enqueue:
        result = await create_and_enqueue_job(
            session, "asset_full_ingest", {"symbol": "AAPL"}
        )

    assert result["id"] == job_id
    mock_enqueue.assert_awaited_once_with(
        session, job_id, "asset_full_ingest", {"symbol": "AAPL"}
    )
