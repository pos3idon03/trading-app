"""Backtest-only advanced explainability (interactions, PDP, slices, tree rules)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from features.ml.explainability import (
    _SHAP_SAMPLE_CAP,
    _TREE_SHAP_MODEL_TYPES,
    _build_explainer,
    _format_shap_values,
    _infer_model_type,
    _positive_class_index,
    _scale_features_for_explainer,
    _uses_scaled_explainer_input,
)
from features.ml.trainer import _resolve_classifier

_PDP_GRID_POINTS = 20
_TOP_INTERACTION_PAIRS = 5
_TREE_RULE_MAX_DEPTH = 4


def enrich_ml_summary_advanced(
    *,
    ml_summary: dict,
    importance_model: Any | None,
    oos_x_rows: list[list[float]],
    oos_bar_indices: list[int],
    trades: list[dict],
    bars: list[dict],
    feature_names: list[str] | None = None,
) -> dict:
    if importance_model is None or not oos_x_rows:
        return ml_summary

    model_type = str(ml_summary.get("model_type") or "")
    resolved_names = list(
        feature_names
        or ml_summary.get("model_feature_names")
        or ml_summary.get("feature_names")
        or []
    )
    classes = [int(value) for value in (ml_summary.get("confusion_labels") or [0, 1])]
    warnings = list(ml_summary.get("macro_warnings") or [])

    advanced: dict[str, Any] = {}
    top_features = _top_shap_feature_names(ml_summary, resolved_names, limit=3)

    try:
        advanced["shap_interactions"] = compute_shap_interactions(
            importance_model,
            oos_x_rows,
            resolved_names,
            model_type=model_type,
        )
    except Exception as exc:
        warnings.append(f"SHAP interactions skipped: {exc}")

    try:
        advanced["partial_dependence"] = compute_pdp_curves(
            importance_model,
            oos_x_rows,
            resolved_names,
            top_features=top_features,
        )
    except Exception as exc:
        warnings.append(f"Partial dependence skipped: {exc}")

    try:
        advanced["shap_slices"] = compute_shap_by_trade_slice(
            importance_model,
            oos_x_rows,
            oos_bar_indices,
            resolved_names,
            classes,
            trades,
            bars,
            model_type=model_type,
        )
    except Exception as exc:
        warnings.append(f"SHAP trade slices skipped: {exc}")

    try:
        advanced["tree_rules"] = export_tree_rules(
            model_type,
            importance_model,
            oos_x_rows,
            resolved_names,
        )
    except Exception as exc:
        warnings.append(f"Tree rules export skipped: {exc}")

    return {**ml_summary, **advanced, "macro_warnings": warnings}


def _top_shap_feature_names(
    ml_summary: dict,
    feature_names: list[str],
    *,
    limit: int,
) -> list[str]:
    shap_rows = ml_summary.get("shap_importance") or []
    ranked = sorted(
        shap_rows,
        key=lambda row: float(row.get("mean_abs_shap") or 0),
        reverse=True,
    )
    names = [str(row["feature"]) for row in ranked if row.get("feature")]
    if names:
        return names[:limit]
    return feature_names[:limit]


def compute_shap_interactions(
    model: Any,
    x_rows: list[list[float]],
    feature_names: list[str],
    *,
    model_type: str,
    top_pairs: int = _TOP_INTERACTION_PAIRS,
) -> list[dict]:
    resolved = _infer_model_type(model, model_type)
    if resolved not in _TREE_SHAP_MODEL_TYPES or not x_rows:
        return []

    try:
        import shap
    except ImportError:  # pragma: no cover
        return []

    sample = x_rows[-min(len(x_rows), _SHAP_SAMPLE_CAP):]
    x_array = np.array(sample)
    explainer = _build_explainer(model, shap, x_array, resolved)
    if explainer is None or not hasattr(explainer, "shap_interaction_values"):
        return []

    values = explainer.shap_interaction_values(x_array)
    matrix = np.asarray(values)
    if matrix.ndim == 4:
        positive = _positive_class_index([0, 1])
        matrix = matrix[:, :, :, positive if matrix.shape[3] > positive else -1]
    strength = np.abs(matrix).mean(axis=0)
    pairs: list[dict] = []
    size = min(len(feature_names), strength.shape[0])
    for i in range(size):
        for j in range(i + 1, size):
            pairs.append({
                "feature_a": feature_names[i],
                "feature_b": feature_names[j],
                "strength": round(float(strength[i, j]), 6),
            })
    pairs.sort(key=lambda item: item["strength"], reverse=True)
    return pairs[:top_pairs]


def compute_pdp_curves(
    model: Any,
    x_rows: list[list[float]],
    feature_names: list[str],
    *,
    top_features: list[str] | None = None,
    grid_points: int = _PDP_GRID_POINTS,
) -> list[dict]:
    if not x_rows or not feature_names:
        return []

    sample = x_rows[-min(len(x_rows), _SHAP_SAMPLE_CAP):]
    x_array = np.array(sample)
    targets = [name for name in (top_features or feature_names) if name in feature_names]
    if not targets:
        return []

    curves: list[dict] = []
    for feature in targets[:3]:
        index = feature_names.index(feature)
        column = x_array[:, index]
        grid = np.linspace(float(column.min()), float(column.max()), grid_points)
        p_up: list[float] = []
        for value in grid:
            modified = x_array.copy()
            modified[:, index] = value
            probs = _predict_positive_probability(model, modified)
            p_up.append(round(float(np.mean(probs)), 6))
        curves.append({
            "feature": feature,
            "grid": [round(float(value), 6) for value in grid],
            "p_up": p_up,
        })
    return curves


def _predict_positive_probability(model: Any, x_array: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(x_array)
        return proba[:, -1]
    preds = model.predict(x_array)
    return np.asarray(preds, dtype=float)


def compute_shap_by_trade_slice(
    model: Any,
    oos_x_rows: list[list[float]],
    oos_bar_indices: list[int],
    feature_names: list[str],
    classes: list[int],
    trades: list[dict],
    bars: list[dict],
    *,
    model_type: str,
) -> dict:
    if not trades or not oos_x_rows or len(oos_bar_indices) != len(oos_x_rows):
        return {}

    bar_to_row = {bar_index: row_index for row_index, bar_index in enumerate(oos_bar_indices)}
    date_to_bar = _build_bar_date_index(bars)
    trade_pnls: list[tuple[int, float]] = []
    for trade in trades:
        entry_date = str(trade.get("entry_date") or "")
        bar_index = date_to_bar.get(entry_date[:10])
        if bar_index is None:
            continue
        row_index = bar_to_row.get(bar_index)
        if row_index is None:
            continue
        trade_pnls.append((row_index, float(trade.get("pnl") or 0)))

    if len(trade_pnls) < 4:
        return {}

    sorted_trades = sorted(trade_pnls, key=lambda item: item[1])
    cut = max(1, len(sorted_trades) // 10)
    winner_rows = [index for index, _ in sorted_trades[-cut:]]
    loser_rows = [index for index, _ in sorted_trades[:cut]]
    row_shap = _per_row_mean_abs_shap(
        model,
        oos_x_rows,
        feature_names,
        classes,
        model_type=model_type,
    )
    if not row_shap:
        return {}

    return {
        "winners_top_decile": _aggregate_row_shap(row_shap, winner_rows, feature_names),
        "losers_bottom_decile": _aggregate_row_shap(row_shap, loser_rows, feature_names),
    }


def _build_bar_date_index(bars: list[dict]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, bar in enumerate(bars):
        time_value = bar.get("time")
        if isinstance(time_value, datetime):
            key = time_value.date().isoformat()
        else:
            key = str(time_value)[:10]
        mapping[key] = index
    return mapping


def _per_row_mean_abs_shap(
    model: Any,
    x_rows: list[list[float]],
    feature_names: list[str],
    classes: list[int],
    *,
    model_type: str,
) -> list[list[float]]:
    resolved = _infer_model_type(model, model_type)
    if resolved in {"ml_knn", "ml_gradient_boosting"}:
        return []

    sample = x_rows[-min(len(x_rows), _SHAP_SAMPLE_CAP):]
    x_array = np.array(sample)
    try:
        import shap
    except ImportError:  # pragma: no cover
        return []

    explainer = _build_explainer(model, shap, x_array, resolved)
    if explainer is None:
        return []

    explain_x = (
        _scale_features_for_explainer(model, x_array)
        if _uses_scaled_explainer_input(model, resolved)
        else x_array
    )
    values = explainer.shap_values(explain_x)
    positive = _positive_class_index(classes)
    matrices: list[np.ndarray] = []
    if isinstance(values, list):
        pick = values[positive] if positive < len(values) else values[-1]
        matrices.append(np.abs(np.asarray(pick)))
    else:
        array = np.abs(np.asarray(values))
        if array.ndim == 3:
            matrices.append(array[:, :, positive if array.shape[2] > positive else -1])
        else:
            matrices.append(array)
    if not matrices:
        return []
    merged = matrices[0]
    return [row.tolist() for row in merged]


def _aggregate_row_shap(
    row_shap: list[list[float]],
    row_indices: list[int],
    feature_names: list[str],
) -> list[dict]:
    if not row_indices:
        return []
    matrix = np.array([row_shap[index] for index in row_indices if index < len(row_shap)])
    if matrix.size == 0:
        return []
    means = matrix.mean(axis=0)
    rows = [
        {"feature": feature_names[i], "mean_abs_shap": round(float(means[i]), 6)}
        for i in range(min(len(feature_names), len(means)))
    ]
    rows.sort(key=lambda item: item["mean_abs_shap"], reverse=True)
    return rows[:10]


def export_tree_rules(
    model_type: str,
    model: Any,
    x_rows: list[list[float]],
    feature_names: list[str],
) -> dict | None:
    resolved = _infer_model_type(model, model_type)
    if resolved not in _TREE_SHAP_MODEL_TYPES or not x_rows:
        return None

    classifier = _resolve_classifier(model)
    text = _export_sklearn_tree_text(classifier, feature_names)
    if text:
        return {"format": "text", "content": text, "max_depth": _TREE_RULE_MAX_DEPTH}

    if resolved == "ml_xgboost":
        xgb_text = _export_xgboost_tree_text(classifier, feature_names)
        if xgb_text:
            return {"format": "text", "content": xgb_text, "max_depth": _TREE_RULE_MAX_DEPTH}
    return None


def _export_sklearn_tree_text(classifier: Any, feature_names: list[str]) -> str | None:
    from sklearn.tree import export_text

    if hasattr(classifier, "estimators_") and classifier.estimators_:
        tree = classifier.estimators_[0]
        return export_text(
            tree,
            feature_names=feature_names,
            max_depth=_TREE_RULE_MAX_DEPTH,
        )
    return None


def _export_xgboost_tree_text(classifier: Any, feature_names: list[str]) -> str | None:
    try:
        import xgboost as xgb
    except ImportError:  # pragma: no cover
        return None
    if not hasattr(classifier, "get_booster"):
        return None
    booster = classifier.get_booster()
    dump = booster.get_dump(with_stats=False)[0]
    lines = dump.split("\n")[:40]
    header = f"# First tree (features: {', '.join(feature_names[:8])}...)\n"
    return header + "\n".join(lines)
