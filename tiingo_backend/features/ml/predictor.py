from dataclasses import dataclass, field
from typing import Any, Optional

from features.ml.feature_preprocessor import FeaturePreprocessor, fit_feature_preprocessor
from features.ml.imbalance import maybe_smote
from features.ml.splitter import build_walk_forward_windows
from features.ml.sparse_event_training import (
    is_sparse_meta_label_training,
    min_train_samples_for_fold,
)
from features.ml.trainer import (
    predict_class_probabilities,
    predict_labels_from_proba,
    predict_proba_up,
    train_model,
)


@dataclass
class WalkForwardResult:
    probabilities: list[Optional[float]]
    class_probabilities: list[Optional[list[float]]]
    class_predictions: list[Optional[int]]
    oos_window_count: int
    mean_oos_accuracy: Optional[float]
    window_accuracies: list[float]
    oos_y_true: list[int]
    oos_y_pred: list[int]
    oos_y_proba: list[list[float]]
    oos_x_rows: list[list[float]]
    oos_bar_indices: list[int]
    model_classes: list[int]
    last_trained_model: Any | None
    pruned_features: list[str] = field(default_factory=list)
    regime_feature_selection: list[dict] = field(default_factory=list)
    explainability_feature_names: list[str] = field(default_factory=list)
    explainability_x_rows: list[list[float]] = field(default_factory=list)
    explainability_bar_indices: list[int] = field(default_factory=list)
    last_preprocessor: FeaturePreprocessor | None = None


def _resolve_feature_names(
    feature_rows: list[Optional[list[float]]],
    feature_names: list[str] | None,
) -> list[str]:
    if feature_names:
        return feature_names
    for row in feature_rows:
        if row is not None:
            return [f"f{i}" for i in range(len(row))]
    return []


def _collect_samples(
    indices: list[int],
    feature_rows: list[Optional[list[float]]],
    labels: list[Optional[int]],
    sample_mask: list[bool] | None = None,
) -> tuple[list[list[float]], list[int], list[int]]:
    x_rows: list[list[float]] = []
    y_rows: list[int] = []
    valid_indices: list[int] = []

    for index in indices:
        if sample_mask is not None and not sample_mask[index]:
            continue
        features = feature_rows[index]
        label = labels[index]
        if features is None or label is None:
            continue
        x_rows.append(features)
        y_rows.append(label)
        valid_indices.append(index)

    return x_rows, y_rows, valid_indices


def _predictions_for_mode(
    model: Any,
    x_rows: list[list[float]],
    label_mode: str,
) -> tuple[list[float], list[list[float]], list[int]]:
    matrix = predict_class_probabilities(model, x_rows)
    classes = list(model.classes_)
    if label_mode == "ternary":
        class_predictions = predict_labels_from_proba(model, x_rows, label_mode="ternary")
        up_probs = [
            row[classes.index(2)] if 2 in classes else row[-1]
            for row in matrix
        ]
        return up_probs, matrix, class_predictions

    up_probs = predict_proba_up(model, x_rows)
    binary_preds = predict_labels_from_proba(model, x_rows, label_mode="binary")
    return up_probs, matrix, binary_preds


def predict_with_frozen_model(
    model: Any,
    feature_rows: list[Optional[list[float]]],
    *,
    label_mode: str = "binary",
    preprocessor: FeaturePreprocessor | None = None,
) -> tuple[list[Optional[float]], list[Optional[list[float]]], list[Optional[int]]]:
    probabilities: list[Optional[float]] = [None] * len(feature_rows)
    class_probabilities: list[Optional[list[float]]] = [None] * len(feature_rows)
    class_predictions: list[Optional[int]] = [None] * len(feature_rows)
    valid_indices: list[int] = []
    x_rows: list[list[float]] = []

    prepared_rows = (
        preprocessor.transform_optional_rows(feature_rows)
        if preprocessor is not None
        else feature_rows
    )
    for index, features in enumerate(prepared_rows):
        if features is None:
            continue
        valid_indices.append(index)
        x_rows.append(features)

    if not x_rows:
        return probabilities, class_probabilities, class_predictions

    up_probs, matrix, preds = _predictions_for_mode(model, x_rows, label_mode)
    for index, prob, row, pred in zip(valid_indices, up_probs, matrix, preds):
        probabilities[index] = prob
        class_probabilities[index] = row
        class_predictions[index] = pred
    return probabilities, class_probabilities, class_predictions


def run_walk_forward_prediction(
    *,
    model_type: str,
    params: dict,
    feature_rows: list[Optional[list[float]]],
    labels: list[Optional[int]],
    train_bars: int,
    test_bars: int,
    step_bars: int,
    sample_mask: list[bool] | None = None,
    feature_names: list[str] | None = None,
    closes: list[float] | None = None,
) -> WalkForwardResult:
    label_mode = str(params.get("label_mode") or "binary")
    bar_count = len(feature_rows)
    names = _resolve_feature_names(feature_rows, feature_names)
    windows = build_walk_forward_windows(bar_count, train_bars, test_bars, step_bars)
    probabilities: list[Optional[float]] = [None] * bar_count
    class_probabilities: list[Optional[list[float]]] = [None] * bar_count
    class_predictions: list[Optional[int]] = [None] * bar_count
    oos_accuracies: list[float] = []
    oos_y_true: list[int] = []
    oos_y_pred: list[int] = []
    oos_y_proba: list[list[float]] = []
    oos_x_rows: list[list[float]] = []
    oos_bar_indices: list[int] = []
    model_classes: list[int] = []
    last_trained_model: Any | None = None
    last_preprocessor: FeaturePreprocessor | None = None
    pruned_all: list[str] = []
    regime_selections: list[dict] = []
    explainability_feature_names: list[str] = []
    explainability_x_rows: list[list[float]] = []
    explainability_bar_indices: list[int] = []

    for train_indices, test_indices in windows:
        x_train, y_train, _ = _collect_samples(
            train_indices,
            feature_rows,
            labels,
            sample_mask,
        )
        x_test, y_test, valid_test_indices = _collect_samples(
            test_indices,
            feature_rows,
            labels,
            sample_mask,
        )
        sparse_events = is_sparse_meta_label_training(params, sample_mask)
        min_samples = min_train_samples_for_fold(
            model_type,
            params,
            sparse_events=sparse_events,
        )
        if len(x_train) < min_samples or len(set(y_train)) < 2:
            continue
        if not x_test:
            continue

        preprocessor = fit_feature_preprocessor(
            x_train,
            y_train,
            names,
            params,
            closes=closes,
            train_indices=train_indices,
        )
        pruned_all.extend(preprocessor.pruned_features)
        if preprocessor.regime_meta:
            regime_selections.append(preprocessor.regime_meta)

        x_train_m = preprocessor.transform(x_train)
        x_test_m = preprocessor.transform(x_test)
        if not x_train_m or not x_train_m[0]:
            continue
        use_smote = params.get("use_smote", True)
        x_train_m, y_train = maybe_smote(
            x_train_m,
            y_train,
            enabled=bool(use_smote),
            model_type=model_type,
        )

        trained = train_model(model_type, x_train_m, y_train, params)
        last_trained_model = trained.model
        last_preprocessor = preprocessor
        model_classes = list(trained.model.classes_)
        up_probs, matrix, preds = _predictions_for_mode(trained.model, x_test_m, label_mode)

        for index, prob, row, pred in zip(valid_test_indices, up_probs, matrix, preds):
            probabilities[index] = prob
            class_probabilities[index] = row
            class_predictions[index] = pred

        oos_y_true.extend(y_test)
        oos_y_pred.extend(preds)
        oos_y_proba.extend(matrix)
        oos_x_rows.extend(x_test_m)
        oos_bar_indices.extend(valid_test_indices)
        explainability_feature_names = list(preprocessor.output_feature_names)
        explainability_x_rows = list(x_test_m)
        explainability_bar_indices = list(valid_test_indices)
        correct = sum(1 for truth, pred in zip(y_test, preds) if truth == pred)
        oos_accuracies.append(correct / len(y_test))

    mean_oos = sum(oos_accuracies) / len(oos_accuracies) if oos_accuracies else None
    return WalkForwardResult(
        probabilities=probabilities,
        class_probabilities=class_probabilities,
        class_predictions=class_predictions,
        oos_window_count=len(oos_accuracies),
        mean_oos_accuracy=mean_oos,
        window_accuracies=oos_accuracies,
        oos_y_true=oos_y_true,
        oos_y_pred=oos_y_pred,
        oos_y_proba=oos_y_proba,
        oos_x_rows=oos_x_rows,
        oos_bar_indices=oos_bar_indices,
        model_classes=model_classes,
        last_trained_model=last_trained_model,
        pruned_features=sorted(set(pruned_all)),
        regime_feature_selection=regime_selections,
        explainability_feature_names=explainability_feature_names,
        explainability_x_rows=explainability_x_rows,
        explainability_bar_indices=explainability_bar_indices,
        last_preprocessor=last_preprocessor,
    )
