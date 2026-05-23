from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_list_ml_models():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/backtest/ml/models")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["models"]) >= 2
    assert any(item["id"] == "ml_logistic" for item in data["models"])
    assert any(item["id"] == "ml_random_forest" for item in data["models"])
    assert any(item["id"] == "ml_gradient_boosting" for item in data["models"])
    logistic = next(item for item in data["models"] if item["id"] == "ml_logistic")
    random_forest = next(item for item in data["models"] if item["id"] == "ml_random_forest")
    assert logistic["supports_hyperparameter_search"] is False
    assert random_forest["supports_hyperparameter_search"] is True


@pytest.mark.asyncio
async def test_run_ml_backtest_enqueues_job():
    job_id = uuid4()
    with patch(
        "routes.backtest_ml.create_and_enqueue_job",
        new=AsyncMock(return_value={"id": job_id}),
    ) as mock_enqueue:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/backtest/ml/run",
                json={
                    "symbol": "AAPL",
                    "model_type": "ml_logistic",
                    "params": {"train_bars": 120, "test_bars": 30, "step_bars": 30},
                },
            )

    assert resp.status_code == 202
    mock_enqueue.assert_awaited_once()
    body = resp.json()
    assert body["job_id"] == str(job_id)
    assert body["status"] == "accepted"


@pytest.mark.asyncio
async def test_ml_data_preview_enqueues_job():
    job_id = uuid4()
    with patch(
        "routes.backtest_ml.create_and_enqueue_job",
        new=AsyncMock(return_value={"id": job_id}),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/backtest/ml/data-preview",
                json={"symbol": "AAPL", "params": {}, "timeframe": "1d"},
            )

    assert resp.status_code == 202
    assert resp.json()["job_id"] == str(job_id)


@pytest.mark.asyncio
async def test_ml_training_export_enqueues_job():
    job_id = uuid4()
    with patch(
        "routes.backtest_ml.create_and_enqueue_job",
        new=AsyncMock(return_value={"id": job_id}),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/backtest/ml/training-data-export",
                json={
                    "symbol": "AAPL",
                    "model_type": "ml_logistic",
                    "params": {"train_bars": 120, "test_bars": 30, "step_bars": 30},
                    "scope": "all_labeled",
                },
            )

    assert resp.status_code == 202
    assert resp.json()["job_id"] == str(job_id)
