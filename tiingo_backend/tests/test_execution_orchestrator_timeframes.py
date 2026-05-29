from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from features.execution.orchestrator import _validate_model_for_deployment


@pytest.mark.asyncio
async def test_validate_model_rejects_unsupported_timeframe(monkeypatch):
    model_id = uuid4()
    monkeypatch.setattr(
        "features.execution.orchestrator.ml_model_dal.get_model",
        AsyncMock(
            return_value={
                "artifact_path": "/tmp/model.pkl",
                "hyperparams": {},
            },
        ),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.extract_saved_model_metadata",
        lambda _row: {"symbol": "AAPL", "timeframe": "1m"},
    )

    with pytest.raises(ValueError, match="Unsupported deployment timeframe"):
        await _validate_model_for_deployment(AsyncMock(), model_id)


@pytest.mark.asyncio
async def test_validate_model_accepts_5m_timeframe(monkeypatch):
    model_id = uuid4()
    monkeypatch.setattr(
        "features.execution.orchestrator.ml_model_dal.get_model",
        AsyncMock(
            return_value={
                "artifact_path": "/tmp/model.pkl",
                "hyperparams": {},
            },
        ),
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.extract_saved_model_metadata",
        lambda _row: {"symbol": "AAPL", "timeframe": "5m"},
    )
    monkeypatch.setattr(
        "features.execution.orchestrator.instrument_dal.get_by_symbol",
        AsyncMock(return_value={"id": 1, "symbol": "AAPL"}),
    )

    row = await _validate_model_for_deployment(AsyncMock(), model_id)
    assert row["artifact_path"] == "/tmp/model.pkl"
