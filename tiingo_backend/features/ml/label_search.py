from typing import Callable

from features.ml.catalog import ML_MODEL_CATALOG
from features.ml.labels import build_labels, label_distribution
from features.ml.predictor import run_walk_forward_prediction
from sklearn.metrics import f1_score

ProgressCallback = Callable[[int], None]

DEFAULT_LABEL_SEARCH_MODEL_TYPES = list(ML_MODEL_CATALOG.keys())


def _label_key(label_mode: str, horizon: int, threshold: float | None) -> str:
    if label_mode == "ternary":
        return f"label_la{horizon}_th{threshold:.3f}"
    return f"label_la{horizon}_binary"


def _sort_results(results: list[dict]) -> list[dict]:
    results.sort(
        key=lambda row: (
            row["f1_macro"] is not None,
            row["f1_macro"] or 0.0,
            row["accuracy"] or 0.0,
        ),
        reverse=True,
    )
    return results


def run_label_grid_search(
    *,
    bars: list[dict],
    feature_rows: list,
    label_mode: str,
    horizons: list[int],
    thresholds: list[float],
    label_method: str = "endpoint",
    train_bars: int,
    test_bars: int,
    step_bars: int,
    model_type: str = "ml_logistic",
    model_label: str | None = None,
) -> list[dict]:
    results: list[dict] = []
    threshold_values = thresholds if label_mode == "ternary" else [0.0]
    resolved_label = model_label or ML_MODEL_CATALOG.get(model_type, {}).get("label", model_type)

    for horizon in horizons:
        for threshold in threshold_values:
            labels = build_labels(
                bars,
                horizon,
                label_mode=label_mode,
                label_threshold=threshold,
                label_method=label_method,
            )
            params = {
                "label_mode": label_mode,
                "label_horizon": horizon,
                "label_threshold": threshold,
                "label_method": label_method,
                "train_bars": train_bars,
                "test_bars": test_bars,
                "step_bars": step_bars,
            }
            walk_forward = run_walk_forward_prediction(
                model_type=model_type,
                params=params,
                feature_rows=feature_rows,
                labels=labels,
                train_bars=train_bars,
                test_bars=test_bars,
                step_bars=step_bars,
            )
            distribution = label_distribution(labels)
            f1_macro = None
            if walk_forward.oos_y_true:
                labels_sorted = sorted(set(walk_forward.oos_y_true) | set(walk_forward.oos_y_pred))
                f1_macro = round(float(f1_score(
                    walk_forward.oos_y_true,
                    walk_forward.oos_y_pred,
                    average="macro",
                    zero_division=0,
                    labels=labels_sorted,
                )), 4)

            base_key = _label_key(label_mode, horizon, threshold if label_mode == "ternary" else None)
            results.append({
                "label_key": f"{model_type}_{base_key}",
                "model_type": model_type,
                "model_label": resolved_label,
                "label_mode": label_mode,
                "label_horizon": horizon,
                "label_threshold": threshold if label_mode == "ternary" else None,
                "accuracy": (
                    round(walk_forward.mean_oos_accuracy, 4)
                    if walk_forward.mean_oos_accuracy is not None
                    else None
                ),
                "f1_macro": f1_macro,
                "oos_window_count": walk_forward.oos_window_count,
                "class_distribution": distribution,
            })

    return _sort_results(results)


def run_multi_model_label_grid_search(
    *,
    bars: list[dict],
    feature_rows: list,
    label_mode: str,
    horizons: list[int],
    thresholds: list[float],
    label_method: str = "endpoint",
    train_bars: int,
    test_bars: int,
    step_bars: int,
    model_types: list[str] | None = None,
    on_model_complete: ProgressCallback | None = None,
) -> list[dict]:
    resolved_models = model_types or DEFAULT_LABEL_SEARCH_MODEL_TYPES
    combined: list[dict] = []
    total_models = len(resolved_models)

    for index, model_type in enumerate(resolved_models):
        combined.extend(run_label_grid_search(
            bars=bars,
            feature_rows=feature_rows,
            label_mode=label_mode,
            horizons=horizons,
            thresholds=thresholds,
            label_method=label_method,
            train_bars=train_bars,
            test_bars=test_bars,
            step_bars=step_bars,
            model_type=model_type,
        ))
        if on_model_complete is not None:
            pct = int(((index + 1) / max(total_models, 1)) * 100)
            on_model_complete(pct)

    return _sort_results(combined)
