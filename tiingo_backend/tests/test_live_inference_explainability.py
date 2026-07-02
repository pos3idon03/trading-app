from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from features.execution.inference_runner import run_live_inference


@pytest.mark.asyncio
async def test_run_live_inference_returns_explainability(monkeypatch):
    model_id = uuid4()
    bars = [{"time": datetime(2026, 5, 28, 15, tzinfo=timezone.utc), "close": 100.0}]
    feature_names = ["ret_1", "rsi_14"]
    feature_rows = [[0.01, 55.0]]

    monkeypatch.setattr(
        "features.execution.inference_runner.ml_model_dal.get_model",
        AsyncMock(
            return_value={
                "model_type": "ml_logistic",
                "feature_mode": "prices_only",
                "hyperparams": {"buy_threshold": 0.6, "sell_threshold": 0.4},
                "artifact_path": "/tmp/model.pkl",
                "feature_schema": {"feature_names": feature_names},
            }
        ),
    )
    monkeypatch.setattr(
        "features.execution.inference_runner.instrument_dal.get_by_symbol",
        AsyncMock(return_value={"id": 1, "symbol": "AAPL"}),
    )
    monkeypatch.setattr(
        "features.execution.inference_runner._load_bars_and_features",
        AsyncMock(
            return_value=(
                bars * 60,
                feature_names,
                feature_rows * 60,
                [],
                [],
                [],
                [],
                [],
                [],
            )
        ),
    )
    monkeypatch.setattr(
        "features.execution.inference_runner.minimum_bars_for_inference",
        lambda _params: 10,
    )
    monkeypatch.setattr(
        "features.execution.inference_runner.validate_feature_schema",
        lambda _schema, _names: None,
    )

    mock_model = MagicMock()
    mock_model.classes_ = [0, 1]
    mock_model.predict_proba.return_value = [[0.3, 0.7]]
    monkeypatch.setattr(
        "features.execution.inference_runner.load_model_bundle",
        lambda _path: (mock_model, None),
    )
    monkeypatch.setattr(
        "features.execution.inference_runner.predict_with_frozen_model",
        lambda *_args, **_kwargs: (
            [None] * 59 + [0.7],
            [None] * 59 + [[0.3, 0.7]],
            [None] * 59 + [1],
        ),
    )
    monkeypatch.setattr(
        "features.execution.inference_runner._resolve_classifier",
        lambda _model: mock_model,
    )
    monkeypatch.setattr(
        "features.execution.inference_runner.compute_instance_contributions",
        lambda *_args, **_kwargs: {
            "method": "shap_linear",
            "top_contributors": [
                {"feature": "ret_1", "value": 0.01, "contribution": 0.05},
            ],
            "warnings": [],
        },
    )

    result = await run_live_inference(
        AsyncMock(),
        model_id=model_id,
        symbol="AAPL",
        timeframe="1h",
        hyperparams={"buy_threshold": 0.6, "sell_threshold": 0.4},
    )

    assert result["probability"] == 0.7
    assert result["explainability"]["method"] == "shap_linear"
    assert result["explainability"]["top_contributors"][0]["feature"] == "ret_1"


def test_last_valid_feature_index_skips_trailing_none_rows():
    from features.execution.inference_runner import _last_valid_feature_index

    rows = [None, [1.0, 2.0], None]
    assert _last_valid_feature_index(rows) == 1
