from typing import Any

import numpy as np
from sklearn.pipeline import Pipeline

from features.ml.trainer import _resolve_classifier

_SHAP_SAMPLE_CAP = 500


def _to_scalar_float(value: Any) -> float:
    arr = np.asarray(value).ravel()
    if arr.size == 0:
        return 0.0
    return float(arr[0])


def compute_shap_importance(
    model: Any,
    x_rows: list[list[float]],
    feature_names: list[str],
    classes: list[int],
) -> list[dict]:
    if not x_rows or not feature_names:
        return []

    sample = x_rows[-min(len(x_rows), _SHAP_SAMPLE_CAP):]
    x_array = np.array(sample)

    try:
        import shap
    except ImportError:  # pragma: no cover
        return []

    explainer = _build_explainer(model, shap, x_array)
    if explainer is None:
        return []

    values = explainer.shap_values(x_array)
    return _format_shap_values(values, feature_names, classes)


def _build_explainer(model: Any, shap_module: Any, x_array: np.ndarray) -> Any | None:
    classifier = _resolve_classifier(model)
    if hasattr(classifier, "feature_importances_"):
        return shap_module.TreeExplainer(classifier)
    if hasattr(classifier, "coef_"):
        scaled_x = _scale_features_for_explainer(model, x_array)
        return shap_module.LinearExplainer(classifier, scaled_x)
    return None


def _scale_features_for_explainer(model: Any, x_array: np.ndarray) -> np.ndarray:
    if isinstance(model, Pipeline):
        scaler = model.named_steps.get("scaler")
        if scaler is not None and hasattr(scaler, "transform"):
            return scaler.transform(x_array)
    return x_array


def _append_feature_rows(
    rows: list[dict],
    means: np.ndarray,
    feature_names: list[str],
    class_label: int | str,
) -> None:
    for feature_index, feature_name in enumerate(feature_names):
        if feature_index >= len(means):
            break
        rows.append({
            "class_label": str(class_label),
            "feature": feature_name,
            "mean_abs_shap": round(_to_scalar_float(means[feature_index]), 6),
        })


def _format_shap_values(
    values: Any,
    feature_names: list[str],
    classes: list[int],
) -> list[dict]:
    rows: list[dict] = []

    if isinstance(values, list):
        for class_index, class_values in enumerate(values):
            class_label = classes[class_index] if class_index < len(classes) else class_index
            means = np.abs(np.asarray(class_values)).mean(axis=0)
            _append_feature_rows(rows, means, feature_names, class_label)
        return rows

    array = np.asarray(values)
    if array.ndim == 3:
        class_count = array.shape[2]
        for class_index in range(class_count):
            class_label = classes[class_index] if class_index < len(classes) else class_index
            means = np.abs(array[:, :, class_index]).mean(axis=0)
            _append_feature_rows(rows, means, feature_names, class_label)
        return rows

    means = np.abs(array).mean(axis=0)
    if means.ndim > 1:
        for class_index in range(means.shape[1]):
            class_label = classes[class_index] if class_index < len(classes) else class_index
            _append_feature_rows(rows, means[:, class_index], feature_names, class_label)
        return rows

    class_label = classes[0] if classes else 0
    _append_feature_rows(rows, means, feature_names, class_label)
    return rows
