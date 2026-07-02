from typing import Any

import numpy as np
from sklearn.pipeline import Pipeline

from features.ml.trainer import _resolve_classifier

_SHAP_SAMPLE_CAP = 500
_TREE_SHAP_MODEL_TYPES = frozenset({"ml_random_forest", "ml_xgboost"})
_LINEAR_SHAP_MODEL_TYPES = frozenset({"ml_logistic"})
_PERMUTATION_GLOBAL_MODEL_TYPES = frozenset({"ml_gradient_boosting", "ml_knn", "ml_lstm"})


def _to_scalar_float(value: Any) -> float:
    arr = np.asarray(value).ravel()
    if arr.size == 0:
        return 0.0
    return float(arr[0])


def _normalize_model_type(model_type: str | None) -> str | None:
    if not model_type:
        return None
    return str(model_type).strip() or None


def _infer_model_type(model: Any, model_type: str | None) -> str | None:
    resolved = _normalize_model_type(model_type)
    if resolved:
        return resolved
    classifier = _resolve_classifier(model)
    type_name = type(classifier).__name__
    if type_name == "XGBClassifier":
        return "ml_xgboost"
    if type_name == "RandomForestClassifier":
        return "ml_random_forest"
    if type_name == "HistGradientBoostingClassifier":
        return "ml_gradient_boosting"
    if type_name == "LogisticRegression":
        return "ml_logistic"
    if type_name == "SafeKNeighborsClassifier":
        return "ml_knn"
    return None


def compute_shap_importance(
    model: Any,
    x_rows: list[list[float]],
    feature_names: list[str],
    classes: list[int],
    *,
    model_type: str | None = None,
) -> list[dict]:
    if not x_rows or not feature_names:
        return []

    resolved_type = _infer_model_type(model, model_type)
    if resolved_type in _PERMUTATION_GLOBAL_MODEL_TYPES:
        return _compute_permutation_importance_rows(
            model,
            x_rows,
            feature_names,
            classes,
        )

    sample = x_rows[-min(len(x_rows), _SHAP_SAMPLE_CAP):]
    x_array = np.array(sample)

    try:
        import shap
    except ImportError:  # pragma: no cover
        return []

    explainer = _build_explainer(model, shap, x_array, resolved_type)
    if explainer is None:
        return []

    explain_x = (
        _scale_features_for_explainer(model, x_array)
        if _uses_scaled_explainer_input(model, resolved_type)
        else x_array
    )
    values = explainer.shap_values(explain_x)
    return _format_shap_values(values, feature_names, classes)


def _compute_permutation_importance_rows(
    model: Any,
    x_rows: list[list[float]],
    feature_names: list[str],
    classes: list[int],
) -> list[dict]:
    try:
        from sklearn.inspection import permutation_importance
    except ImportError:  # pragma: no cover
        return []

    sample = x_rows[-min(len(x_rows), _SHAP_SAMPLE_CAP):]
    x_array = np.array(sample)
    if x_array.shape[0] < 2:
        return []

    y_true = model.predict(x_array)
    if len(set(y_true.tolist())) < 2:
        return []

    result = permutation_importance(
        model,
        x_array,
        y_true,
        n_repeats=5,
        random_state=42,
        n_jobs=1,
    )
    class_label = str(_default_class_for_single_matrix(classes))
    rows: list[dict] = []
    for index, feature_name in enumerate(feature_names):
        if index >= len(result.importances_mean):
            break
        rows.append({
            "class_label": class_label,
            "feature": feature_name,
            "mean_abs_shap": round(float(abs(result.importances_mean[index])), 6),
        })
    rows.sort(key=lambda item: item["mean_abs_shap"], reverse=True)
    return rows


def _build_explainer(
    model: Any,
    shap_module: Any,
    x_array: np.ndarray,
    model_type: str | None,
) -> Any | None:
    resolved_type = _infer_model_type(model, model_type)
    classifier = _resolve_classifier(model)

    if resolved_type in _TREE_SHAP_MODEL_TYPES:
        if hasattr(classifier, "get_booster") or hasattr(classifier, "estimators_"):
            return shap_module.TreeExplainer(classifier)
        return None

    if resolved_type in _LINEAR_SHAP_MODEL_TYPES:
        if hasattr(classifier, "coef_"):
            scaled_x = _scale_features_for_explainer(model, x_array)
            return shap_module.LinearExplainer(classifier, scaled_x)
        return None

    return None


def _uses_scaled_explainer_input(model: Any, model_type: str | None) -> bool:
    resolved_type = _infer_model_type(model, model_type)
    return resolved_type in _LINEAR_SHAP_MODEL_TYPES


def _scale_features_for_explainer(model: Any, x_array: np.ndarray) -> np.ndarray:
    if isinstance(model, Pipeline):
        scaler = model.named_steps.get("scaler")
        if scaler is not None and hasattr(scaler, "transform"):
            return scaler.transform(x_array)
    return x_array


def _default_class_for_single_matrix(classes: list[int]) -> int | str:
    if len(classes) >= 2:
        return classes[-1]
    return classes[0] if classes else 0


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
        if len(values) == 1 and len(classes) == 2:
            means = np.abs(np.asarray(values[0])).mean(axis=0)
            _append_feature_rows(
                rows,
                means,
                feature_names,
                _default_class_for_single_matrix(classes),
            )
            return rows
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

    class_label = _default_class_for_single_matrix(classes)
    _append_feature_rows(rows, means, feature_names, class_label)
    return rows


def _positive_class_index(classes: list[int]) -> int:
    if 2 in classes:
        return classes.index(2)
    if 1 in classes:
        return classes.index(1)
    return max(len(classes) - 1, 0)


def _explainer_method(model: Any, model_type: str | None = None) -> str:
    resolved_type = _infer_model_type(model, model_type)
    if resolved_type in _TREE_SHAP_MODEL_TYPES:
        return "shap_tree"
    if resolved_type in _LINEAR_SHAP_MODEL_TYPES:
        return "shap_linear"
    if resolved_type in _PERMUTATION_GLOBAL_MODEL_TYPES:
        return "permutation_global"
    return "unavailable"


def _extract_signed_shap_row(
    values: Any,
    classes: list[int],
    positive_index: int,
) -> list[float]:
    if isinstance(values, list):
        if not values:
            raise ValueError("SHAP returned no class outputs")
        if len(values) == 1 and len(classes) == 2:
            matrix = np.asarray(values[0])
            if matrix.ndim == 1:
                return [float(value) for value in matrix]
            if matrix.shape[0] == 1:
                return [float(value) for value in matrix[0]]
            return [float(value) for value in matrix[0]]
        class_index = positive_index if positive_index < len(values) else len(values) - 1
        target = np.asarray(values[class_index])
        if target.ndim == 1:
            return [float(value) for value in target]
        if target.shape[0] == 1:
            return [float(value) for value in target[0]]
        return [float(value) for value in target[0]]

    array = np.asarray(values)
    if array.size == 0:
        raise ValueError("SHAP returned empty values")
    if array.ndim == 3:
        class_dim = array.shape[2]
        class_index = positive_index if positive_index < class_dim else class_dim - 1
        return [float(value) for value in array[0, :, class_index]]
    if array.ndim == 2:
        if array.shape[0] == 1:
            return [float(value) for value in array[0]]
        return [float(value) for value in array[-1]]
    return [float(value) for value in array.ravel()]


def _ordered_contributors(
    shap_row: list[float],
    x_row: list[float],
    feature_names: list[str],
    *,
    top_n: int | None = None,
) -> list[dict]:
    rows: list[dict] = []
    for index, feature_name in enumerate(feature_names):
        if index >= len(shap_row) or index >= len(x_row):
            break
        rows.append({
            "feature": feature_name,
            "value": round(float(x_row[index]), 6),
            "contribution": round(float(shap_row[index]), 6),
        })
    rows.sort(key=lambda item: abs(item["contribution"]), reverse=True)
    if top_n is not None:
        return rows[:top_n]
    return rows


def _extract_base_value(explainer: Any, classes: list[int]) -> float | None:
    expected = getattr(explainer, "expected_value", None)
    if expected is None:
        return None
    positive_index = _positive_class_index(classes)
    if isinstance(expected, (list, tuple, np.ndarray)):
        values = list(np.asarray(expected).ravel())
        if not values:
            return None
        index = positive_index if positive_index < len(values) else len(values) - 1
        return round(float(values[index]), 6)
    return round(float(expected), 6)


def _unavailable_explainability(warnings: list[str]) -> dict:
    return {
        "method": "unavailable",
        "base_value": None,
        "predicted_value": None,
        "top_contributors": [],
        "ordered_contributors": [],
        "warnings": warnings,
    }


def compute_instance_contributions(
    model: Any,
    x_row: list[float],
    background_rows: list[list[float]],
    feature_names: list[str],
    classes: list[int],
    *,
    model_type: str | None = None,
    top_n: int = 5,
    ordered_top_n: int = 15,
) -> dict:
    method = _explainer_method(model, model_type)
    if not x_row or not feature_names:
        return _unavailable_explainability(["No feature data for explainability"])
    if method in ("unavailable", "permutation_global"):
        warning = (
            "Model type does not support live SHAP explainability"
            if method == "permutation_global"
            else "Model type does not support SHAP explainability"
        )
        return _unavailable_explainability([warning])
    if not background_rows:
        return _unavailable_explainability(["Insufficient background rows for SHAP"])

    try:
        import shap
    except ImportError:  # pragma: no cover
        return _unavailable_explainability(["SHAP not installed"])

    sample = background_rows[-min(len(background_rows), _SHAP_SAMPLE_CAP):]
    background = np.array(sample)
    instance = np.array([x_row])
    resolved_type = _infer_model_type(model, model_type)
    explainer = _build_explainer(model, shap, background, resolved_type)
    if explainer is None:
        return _unavailable_explainability(["Could not build SHAP explainer"])

    scaled = _uses_scaled_explainer_input(model, resolved_type)
    explain_x = _scale_features_for_explainer(model, instance) if scaled else instance
    try:
        values = explainer.shap_values(explain_x)
    except Exception as exc:
        return _unavailable_explainability([f"SHAP explainability failed: {exc}"])

    try:
        shap_row = _extract_signed_shap_row(values, classes, _positive_class_index(classes))
    except (IndexError, ValueError) as exc:
        return _unavailable_explainability([f"SHAP explainability parse failed: {exc}"])

    base_value = _extract_base_value(explainer, classes)
    predicted_value = (
        round(base_value + sum(shap_row), 6) if base_value is not None else None
    )
    ordered = _ordered_contributors(
        shap_row,
        x_row,
        feature_names,
        top_n=ordered_top_n,
    )
    return {
        "method": method,
        "base_value": base_value,
        "predicted_value": predicted_value,
        "top_contributors": ordered[:top_n],
        "ordered_contributors": ordered,
        "warnings": [],
    }
