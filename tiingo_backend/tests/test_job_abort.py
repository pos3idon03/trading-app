from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from features.worker.job_abort import abort_ingestion_arq_job


@pytest.mark.asyncio
async def test_abort_ingestion_arq_job_heavy_queue():
    job_id = uuid4()
    mock_pool = AsyncMock()
    mock_job = MagicMock()
    mock_job.abort = AsyncMock(return_value=True)

    with patch(
        "features.worker.job_abort.get_arq_pool",
        new=AsyncMock(return_value=mock_pool),
    ), patch(
        "features.worker.job_abort.Job",
        return_value=mock_job,
    ) as job_cls:
        aborted = await abort_ingestion_arq_job(job_id, "ml_data_preview")

    assert aborted is True
    job_cls.assert_called_once_with(str(job_id), mock_pool, _queue_name="heavy")
    assert mock_job.abort.await_count >= 1


@pytest.mark.asyncio
async def test_abort_ingestion_arq_job_default_queue():
    job_id = uuid4()
    mock_pool = AsyncMock()
    mock_job = MagicMock()
    mock_job.abort = AsyncMock(return_value=True)

    with patch(
        "features.worker.job_abort.get_arq_pool",
        new=AsyncMock(return_value=mock_pool),
    ), patch(
        "features.worker.job_abort.Job",
        return_value=mock_job,
    ) as job_cls:
        aborted = await abort_ingestion_arq_job(job_id, "ohlcv_backfill")

    assert aborted is True
    job_cls.assert_called_once_with(str(job_id), mock_pool, _queue_name="arq:queue")


@pytest.mark.asyncio
async def test_cancel_job_route_aborts_arq_task():
    from httpx import ASGITransport, AsyncClient

    from db import get_db
    from main import app

    job_id = uuid4()
    cancelled = {
        "id": job_id,
        "job_type": "ml_data_preview",
        "status": "cancelled",
        "progress": 35,
        "params": {"symbol": "MSFT"},
        "result": None,
        "error_message": "Cancelled by user",
        "started_at": None,
        "finished_at": "2024-01-01T00:00:00+00:00",
        "created_at": "2024-01-01T00:00:00+00:00",
    }

    async def _fake_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = _fake_db
    try:
        with patch(
            "routes.ingestion.job_dal.cancel_job",
            new=AsyncMock(return_value=cancelled),
        ), patch(
            "features.worker.job_abort.abort_ingestion_arq_job",
            new=AsyncMock(return_value=True),
        ) as abort_mock:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/api/v1/ingestion/jobs/{job_id}/cancel")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    abort_mock.assert_awaited_once_with(job_id, "ml_data_preview")
