from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from features.execution.inference_runner import run_live_inference


def _bar(close: float = 100.0) -> dict:
    return {
        "time": datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 1.0,
    }


@pytest.mark.asyncio
async def test_live_inference_uses_meta_gate_signals():
    model_id = uuid4()
    saved = {
        "id": model_id,
        "model_type": "xgboost",
        "artifact_path": "/tmp/model.pkl",
        "hyperparams": {"label_mode": "meta_label", "meta_gate_threshold": 0.7},
        "feature_schema": {"feature_names": ["f1"]},
    }
    instrument = {"id": 1, "symbol": "BTC-USD", "asset_type": "crypto"}
    bars = [_bar() for _ in range(400)]
    feature_rows = [[1.0] for _ in bars]
    event_mask = [False] * (len(bars) - 1) + [True]
    probabilities = [None] * (len(bars) - 1) + [0.8]

    mock_model = MagicMock()
    mock_model.classes_ = [0, 1]

    with patch(
        "features.execution.inference_runner.ml_model_dal.get_model",
        new=AsyncMock(return_value=saved),
    ), patch(
        "features.execution.inference_runner.instrument_dal.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "features.execution.inference_runner.validate_ml_params",
        return_value={
            "label_mode": "meta_label",
            "meta_gate_threshold": 0.7,
            "buy_threshold": 0.65,
            "sell_threshold": 0.35,
            "train_bars": 100,
            "test_bars": 20,
            "step_bars": 20,
            "label_horizon": 5,
            "max_horizon_bars": 48,
            "base_strategy_id": "crypto_trend_entry",
            "base_strategy_params": {},
        },
    ), patch(
        "features.execution.inference_runner.validate_inference_params",
        return_value=None,
    ), patch(
        "features.execution.inference_runner._load_bars_and_features",
        new=AsyncMock(
            return_value=(bars, ["f1"], feature_rows, [], [], [], [], [], []),
        ),
    ), patch(
        "features.execution.inference_runner.load_model_bundle",
        return_value=(mock_model, None),
    ), patch(
        "features.execution.inference_runner.predict_with_frozen_model",
        return_value=(probabilities, [None] * len(bars), [None] * len(bars)),
    ), patch(
        "features.execution.inference_runner.build_event_mask",
        return_value=event_mask,
    ), patch(
        "features.execution.inference_runner.meta_gate_signals",
        return_value=["hold"] * (len(bars) - 1) + ["buy"],
    ) as meta_gate, patch(
        "features.execution.inference_runner._resolve_classifier",
        return_value=mock_model,
    ), patch(
        "features.execution.inference_runner.compute_instance_contributions",
        return_value={"method": "shap", "top_contributors": [], "warnings": []},
    ):
        result = await run_live_inference(
            AsyncMock(),
            model_id=model_id,
            symbol="BTC-USD",
            timeframe="1h",
            hyperparams={},
        )

    meta_gate.assert_called_once()
    assert result["signal"] == "buy"
    assert result["label_mode"] == "meta_label"
