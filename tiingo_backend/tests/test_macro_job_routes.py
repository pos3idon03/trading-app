from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_macro_backfill_enqueues_job():
    job_id = uuid4()
    with patch(
        "routes.macro.create_and_enqueue_job",
        new=AsyncMock(return_value={"id": job_id}),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/ingestion/macro/backfill",
                json={"series_ids": ["DGS10", "GDP"]},
            )

    assert resp.status_code == 202
    assert resp.json()["job_id"] == str(job_id)


@pytest.mark.asyncio
async def test_macro_refresh_enqueues_job():
    job_id = uuid4()
    with patch(
        "routes.macro.create_and_enqueue_job",
        new=AsyncMock(return_value={"id": job_id}),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/ingestion/macro/refresh")

    assert resp.status_code == 202
    assert resp.json()["job_id"] == str(job_id)


@pytest.mark.asyncio
async def test_macro_seed_enqueues_job():
    job_id = uuid4()
    with patch(
        "routes.macro.create_and_enqueue_job",
        new=AsyncMock(return_value={"id": job_id}),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/ingestion/macro/seed")

    assert resp.status_code == 202
    assert resp.json()["job_id"] == str(job_id)


@pytest.mark.asyncio
async def test_macro_alfred_backfill_enqueues_job():
    job_id = uuid4()
    with patch(
        "routes.macro.create_and_enqueue_job",
        new=AsyncMock(return_value={"id": job_id}),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/ingestion/macro/alfred-backfill",
                json={"series_ids": ["CPIAUCSL", "DFF"]},
            )

    assert resp.status_code == 202
    assert resp.json()["job_id"] == str(job_id)
