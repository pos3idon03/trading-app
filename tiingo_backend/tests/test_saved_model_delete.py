from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from features.ml.artifacts import delete_model_artifact, save_model_artifact
from main import app
from sklearn.linear_model import LogisticRegression


@pytest.mark.asyncio
async def test_delete_saved_model_route_returns_204():
    model_id = uuid4()
    with patch(
        "routes.backtest_ml.delete_saved_ml_model",
        new=AsyncMock(return_value=None),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/backtest/ml/saved-models/{model_id}")

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_saved_model_route_returns_404_when_missing():
    model_id = uuid4()
    with patch(
        "routes.backtest_ml.delete_saved_ml_model",
        new=AsyncMock(side_effect=LookupError(f"Saved model not found: {model_id}")),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/backtest/ml/saved-models/{model_id}")

    assert resp.status_code == 404


def test_delete_model_artifact_removes_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ML_ARTIFACT_DIR", str(tmp_path))
    from config import get_settings

    get_settings.cache_clear()

    model = LogisticRegression(max_iter=200, random_state=42)
    model.fit([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6], [0.7, 0.8]], [0, 1, 0, 1])
    model_id = uuid4()
    path = save_model_artifact(model, model_id)

    delete_model_artifact(path)

    assert not tmp_path.joinpath(f"{model_id}.joblib").exists()
    get_settings.cache_clear()


def test_delete_model_artifact_ignores_missing_path():
    delete_model_artifact("/tmp/does-not-exist-model.joblib")


@pytest.mark.asyncio
async def test_delete_saved_ml_model_orchestrator(tmp_path, monkeypatch):
    monkeypatch.setenv("ML_ARTIFACT_DIR", str(tmp_path))
    from config import get_settings

    get_settings.cache_clear()

    model_id = uuid4()
    model = LogisticRegression(max_iter=200, random_state=42)
    model.fit([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6], [0.7, 0.8]], [0, 1, 0, 1])
    artifact_path = save_model_artifact(model, model_id)

    deleted_row = {
        "id": model_id,
        "name": "Test",
        "model_type": "ml_logistic",
        "feature_mode": "prices_only",
        "feature_schema": {},
        "hyperparams": {},
        "train_metrics": None,
        "artifact_path": artifact_path,
        "created_at": datetime.now(timezone.utc),
    }

    session = AsyncMock()
    session.commit = AsyncMock()

    with patch(
        "features.ml.orchestrator.ml_model_dal.delete_model",
        new=AsyncMock(return_value=deleted_row),
    ):
        from features.ml.orchestrator import delete_saved_ml_model

        await delete_saved_ml_model(session, model_id)

    session.commit.assert_awaited_once()
    assert not tmp_path.joinpath(f"{model_id}.joblib").exists()
    get_settings.cache_clear()
