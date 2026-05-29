from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import instrument_dal, ml_model_dal
from features.ml.artifacts import (
    align_feature_matrix_to_schema,
    load_model_artifact,
    validate_feature_schema,
)
from features.ml.catalog import (
    minimum_bars_for_inference,
    validate_inference_params,
    validate_ml_params,
)
from features.ml.orchestrator import _load_bars_and_features
from features.ml.predictor import predict_with_frozen_model
from features.ml.explainability import compute_instance_contributions
from features.ml.meta_label_events import build_event_mask
from features.ml.signals import meta_gate_signals, predictions_to_signals
from features.ml.trainer import _resolve_classifier
from features.backtesting.bar_loader import validate_timeframe
from features.execution.deployment_timeframes import validate_execution_timeframe


def _bar_time(bar: dict) -> datetime:
    value = bar["time"]
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _last_price(bars: list[dict]) -> float | None:
    if not bars:
        return None
    close = bars[-1].get("close")
    return float(close) if close is not None else None


def _last_valid_feature_index(feature_rows: list) -> int | None:
    for index in range(len(feature_rows) - 1, -1, -1):
        if feature_rows[index] is not None:
            return index
    return None


async def run_live_inference(
    session: AsyncSession,
    *,
    model_id: UUID,
    symbol: str,
    timeframe: str,
    hyperparams: dict,
) -> dict[str, Any]:
    saved = await ml_model_dal.get_model(session, model_id)
    if not saved:
        raise ValueError(f"Saved model not found: {model_id}")
    if not saved.get("artifact_path"):
        raise ValueError(f"Saved model {model_id} has no artifact on disk")

    validate_timeframe(timeframe, "decision timeframe")
    validate_execution_timeframe(timeframe)

    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    asset_type = str(instrument.get("asset_type") or "equity")
    merged_params = {**(saved.get("hyperparams") or {}), **hyperparams}
    validated_params = validate_ml_params(
        saved["model_type"],
        merged_params,
        timeframe,
        asset_type=asset_type,
    )
    validate_inference_params(saved, validated_params)

    end = datetime.now(timezone.utc)
    min_bars = minimum_bars_for_inference(validated_params)
    (
        bars,
        feature_names,
        feature_rows,
        macro_warnings,
        fundamental_warnings,
        _macro_ids,
        _fundamental_metrics,
        context_warnings,
        strategy_warnings,
    ) = await _load_bars_and_features(
        session,
        instrument=instrument,
        validated_params=validated_params,
        timeframe=timeframe,
        start=None,
        end=end,
        min_bars=min_bars,
    )

    feature_names, feature_rows = align_feature_matrix_to_schema(
        saved["feature_schema"],
        feature_names,
        feature_rows,
    )
    validate_feature_schema(saved["feature_schema"], feature_names)
    if len(feature_rows) != len(bars):
        raise ValueError(
            f"Feature row count ({len(feature_rows)}) does not match bar count ({len(bars)})"
        )

    last_index = _last_valid_feature_index(feature_rows)
    if last_index is None:
        raise ValueError("No usable features for latest bar")

    label_mode = str(validated_params.get("label_mode") or "binary")
    model = load_model_artifact(saved["artifact_path"])
    probabilities, class_probabilities, class_predictions = predict_with_frozen_model(
        model,
        feature_rows,
        label_mode=label_mode,
    )

    last_prob = probabilities[last_index]
    last_class_pred = class_predictions[last_index]
    last_class_probs = class_probabilities[last_index]
    last_features = feature_rows[last_index]
    background_rows = [
        row for row in feature_rows[: last_index + 1] if row is not None
    ]
    classes = list(_resolve_classifier(model).classes_)
    explainability = compute_instance_contributions(
        model,
        last_features,
        background_rows,
        feature_names,
        classes,
    ) if last_features is not None else {
        "method": "unavailable",
        "top_contributors": [],
        "warnings": ["Latest bar has no usable features"],
    }
    min_class_probability = validated_params.get("min_class_probability")
    min_class_prob = float(min_class_probability) if min_class_probability is not None else None

    if label_mode == "meta_label":
        event_mask = build_event_mask(bars, validated_params)
        gate_threshold = float(validated_params.get("meta_gate_threshold", 0.65))
        signals = meta_gate_signals(event_mask, probabilities, gate_threshold)
    else:
        signals = predictions_to_signals(
            label_mode=label_mode,
            probabilities=probabilities,
            class_predictions=class_predictions,
            buy_threshold=float(validated_params["buy_threshold"]),
            sell_threshold=float(validated_params["sell_threshold"]),
            min_class_probability=min_class_prob,
            class_probabilities=class_probabilities,
        )
    signal = signals[last_index]
    bar_time = _bar_time(bars[last_index])

    return {
        "signal": signal,
        "label_mode": label_mode,
        "bar_time": bar_time,
        "probability": last_prob,
        "class_prediction": last_class_pred,
        "class_probabilities": last_class_probs,
        "explainability": explainability,
        "last_price": _last_price(bars),
        "warnings": [*macro_warnings, *fundamental_warnings, *context_warnings, *strategy_warnings],
    }
