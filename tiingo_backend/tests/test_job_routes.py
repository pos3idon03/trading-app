from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from db import get_db
from main import app


async def _fake_db_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    yield session


@pytest.mark.asyncio
async def test_list_jobs_with_status_filter():
    jobs = [
        {
            "id": uuid4(),
            "job_type": "ohlcv_backfill",
            "status": "failed",
            "progress": 0,
            "params": {},
            "result": None,
            "error_message": "err",
            "started_at": None,
            "finished_at": None,
            "created_at": "2024-01-01T00:00:00+00:00",
        }
    ]

    with patch(
        "routes.ingestion.job_dal.list_jobs",
        new=AsyncMock(return_value=jobs),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ingestion/jobs?status=failed")

    assert resp.status_code == 200
    assert resp.json()[0]["status"] == "failed"


@pytest.mark.asyncio
async def test_list_active_jobs():
    with patch(
        "routes.ingestion.job_dal.list_active_jobs",
        new=AsyncMock(return_value=[]),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ingestion/jobs/active")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_cancel_job_success():
    job_id = uuid4()
    cancelled = {
        "id": job_id,
        "job_type": "ml_data_preview",
        "status": "cancelled",
        "progress": 5,
        "params": {"symbol": "BTC-USD"},
        "result": None,
        "error_message": "Cancelled by user",
        "started_at": None,
        "finished_at": "2024-01-01T00:00:00+00:00",
        "created_at": "2024-01-01T00:00:00+00:00",
    }

    app.dependency_overrides[get_db] = _fake_db_session
    try:
        with patch(
            "routes.ingestion.job_dal.cancel_job",
            new=AsyncMock(return_value=cancelled),
        ), patch(
            "features.worker.job_abort.abort_ingestion_arq_job",
            new=AsyncMock(return_value=True),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/api/v1/ingestion/jobs/{job_id}/cancel")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_job_conflict_when_not_active():
    job_id = uuid4()

    app.dependency_overrides[get_db] = _fake_db_session
    try:
        with patch(
            "routes.ingestion.job_dal.cancel_job",
            new=AsyncMock(return_value=None),
        ), patch(
            "routes.ingestion.job_dal.get_job",
            new=AsyncMock(
                return_value={
                    "id": job_id,
                    "job_type": "ml_data_preview",
                    "status": "completed",
                    "progress": 100,
                    "params": {},
                    "result": {},
                    "error_message": None,
                    "started_at": None,
                    "finished_at": None,
                    "created_at": "2024-01-01T00:00:00+00:00",
                }
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/api/v1/ingestion/jobs/{job_id}/cancel")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_instrument_enqueues_full_ingest():
    instrument = {
        "id": 1,
        "symbol": "AAPL",
        "tiingo_ticker": "AAPL",
        "name": "Apple",
        "asset_type": "stock",
        "exchange": "NASDAQ",
        "currency": "USD",
        "is_active": True,
        "metadata": None,
    }
    job_id = uuid4()

    with patch(
        "routes.instruments.instrument_dal.upsert_instrument",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "routes.instruments.create_and_enqueue_job",
        new=AsyncMock(return_value={"id": job_id}),
    ), patch(
        "routes.instruments.get_settings",
    ) as mock_settings:
        mock_settings.return_value.auto_backfill_on_create = True
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/instruments",
                json={
                    "symbol": "AAPL",
                    "asset_type": "stock",
                    "name": "Apple",
                    "auto_ingest": True,
                },
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["job_id"] == str(job_id)
