from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_train_route_enqueues_job():
    job_id = uuid4()
    with patch(
        "routes.backtest_ml.create_and_enqueue_job",
        new=AsyncMock(return_value={"id": job_id}),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/backtest/ml/train",
                json={"symbol": "AAPL", "model_type": "ml_logistic"},
            )

    assert resp.status_code == 202
    body = resp.json()
    assert body["job_id"] == str(job_id)
    assert body["status"] == "accepted"


@pytest.mark.asyncio
async def test_list_saved_models_route():
    model_id = uuid4()
    now = datetime.now(timezone.utc)
    mock_rows = [
        {
            "id": model_id,
            "name": "Saved model",
            "model_type": "ml_random_forest",
            "feature_mode": "prices_only",
            "feature_schema": {"feature_names": ["ret_1d"], "version": 1},
            "hyperparams": {},
            "train_metrics": {
                "accuracy": 0.7,
                "training_symbol": "AAPL",
                "timeframe": "1d",
            },
            "created_at": now,
        }
    ]

    with patch(
        "routes.backtest_ml.list_saved_ml_models",
        new=AsyncMock(return_value=mock_rows),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/backtest/ml/saved-models")

    assert resp.status_code == 200
    assert len(resp.json()["models"]) == 1
    assert resp.json()["models"][0]["id"] == str(model_id)
    assert resp.json()["models"][0]["symbol"] == "AAPL"
    assert resp.json()["models"][0]["timeframe"] == "1d"
