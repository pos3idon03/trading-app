from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from features.ml import orchestrator


@pytest.mark.asyncio
async def test_inference_backtest_shap_uses_preprocessed_features():
    model_id = uuid4()
    raw_features = [1.0, 2.0, 3.0, 4.0, 5.0]
    captured: dict = {}

    def _capture_shap(
        model,
        x_rows,
        feature_names,
        classes,
        *,
        model_type=None,
    ):
        captured["x_rows"] = x_rows
        captured["feature_names"] = feature_names
        return []

    preprocessor = MagicMock()
    preprocessor.output_feature_names = ["pc_1", "pc_2"]
    preprocessor.transform.return_value = [[0.1, 0.2]]

    model = MagicMock()
    model.classes_ = [0, 1]

    saved = {
        "model_type": "ml_xgboost",
        "artifact_path": "/tmp/fake-model",
        "feature_schema": {"feature_names": ["f0", "f1", "f2", "f3", "f4"]},
    }

    with (
        patch.object(
            orchestrator.ml_model_dal,
            "get_model",
            new=AsyncMock(return_value=saved),
        ),
        patch.object(orchestrator, "validate_inference_params"),
        patch.object(orchestrator, "validate_feature_schema"),
        patch.object(
            orchestrator,
            "load_model_bundle",
            return_value=(model, preprocessor),
        ),
        patch.object(
            orchestrator,
            "predict_with_frozen_model",
            return_value=([0.6], [[0.4, 0.6]], [1]),
        ),
        patch.object(
            orchestrator,
            "compute_shap_importance",
            side_effect=_capture_shap,
        ),
        patch.object(
            orchestrator,
            "extract_feature_importance",
            return_value=[],
        ),
    ):
        _signals, ml_summary, _model_type = await orchestrator._run_inference_backtest(
            session=AsyncMock(),
            model_id=model_id,
            validated_params={
                "feature_mode": "prices_only",
                "label_mode": "binary",
                "buy_threshold": 0.55,
                "sell_threshold": 0.45,
            },
            feature_names=["f0", "f1", "f2", "f3", "f4"],
            feature_rows=[raw_features],
            labels=[1],
            bars=[{"close": 100.0, "time": "2026-01-01"}],
            macro_series_ids=[],
            macro_warnings=[],
            fundamental_metrics=[],
            fundamental_warnings=[],
            eval_start_index=0,
        )

    preprocessor.transform.assert_called_once_with([raw_features])
    assert captured["x_rows"] == [[0.1, 0.2]]
    assert captured["feature_names"] == ["pc_1", "pc_2"]
    assert "SHAP explainability skipped" not in " ".join(ml_summary.get("macro_warnings") or [])
