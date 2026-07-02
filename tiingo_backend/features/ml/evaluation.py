from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    auc,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def compute_classification_metrics(
    y_true: list[int],
    y_pred: list[int],
    *,
    average: str = "binary",
) -> dict:
    if not y_true:
        return {
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "f1_macro": None,
        }
    labels = sorted(set(y_true) | set(y_pred))
    avg = "macro" if len(labels) > 2 else "binary"
    pos_label = 1 if 1 in labels else labels[-1]
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(
            y_true, y_pred, average=avg, zero_division=0, labels=labels,
        )), 4),
        "recall": round(float(recall_score(
            y_true, y_pred, average=avg, zero_division=0, labels=labels,
        )), 4),
        "f1": round(float(f1_score(
            y_true, y_pred, average=avg, zero_division=0, labels=labels,
        )), 4),
        "f1_macro": round(float(f1_score(
            y_true, y_pred, average="macro", zero_division=0, labels=labels,
        )), 4),
    }


def build_confusion_matrix(
    y_true: list[int],
    y_pred: list[int],
    *,
    labels: list[int] | None = None,
) -> list[list[int]]:
    if not y_true:
        size = len(labels) if labels else 2
        return [[0] * size for _ in range(size)]
    resolved = labels or sorted(set(y_true) | set(y_pred))
    matrix = confusion_matrix(y_true, y_pred, labels=resolved)
    return [[int(value) for value in row] for row in matrix.tolist()]


def _resolve_classifier(model: Any) -> Any:
    from sklearn.pipeline import Pipeline

    if isinstance(model, Pipeline):
        classifier = model.named_steps.get("classifier")
        if classifier is not None:
            return classifier
    return model


def extract_feature_importance(model: Any, feature_names: list[str]) -> list[dict]:
    classifier = _resolve_classifier(model)
    importances = getattr(classifier, "feature_importances_", None)
    if importances is None:
        return []

    pairs = sorted(
        zip(feature_names, importances),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    return [
        {"name": name, "value": round(float(value), 6)}
        for name, value in pairs
    ]


def extract_coefficient_importance(model: Any, feature_names: list[str]) -> list[dict]:
    classifier = _resolve_classifier(model)
    coef = getattr(classifier, "coef_", None)
    if coef is None:
        return []

    matrix = np.asarray(coef)
    if matrix.ndim == 1:
        weights = np.abs(matrix)
    else:
        weights = np.abs(matrix).mean(axis=0)

    pairs = sorted(
        zip(feature_names, weights),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    return [
        {"name": name, "value": round(float(value), 6)}
        for name, value in pairs
    ]


def supports_feature_importance_model(model: Any) -> bool:
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier

    return isinstance(model, (RandomForestClassifier, HistGradientBoostingClassifier))


def build_roc_curves(
    y_true: list[int],
    y_proba: list[list[float]],
    classes: list[int],
) -> tuple[list[dict], dict[str, float | None]]:
    if not y_true or not y_proba:
        return [], {}

    curves: list[dict] = []
    auc_scores: dict[str, float | None] = {}

    if len(classes) == 2:
        positive = classes[-1]
        positive_index = classes.index(positive)
        scores = [row[positive_index] for row in y_proba]
        fpr, tpr, _ = roc_curve(y_true, scores, pos_label=positive)
        score = roc_auc_score(y_true, scores)
        curves.append({
            "class_label": str(positive),
            "fpr": [round(float(v), 6) for v in fpr],
            "tpr": [round(float(v), 6) for v in tpr],
            "auc": round(float(score), 4),
        })
        auc_scores[f"class_{positive}"] = round(float(score), 4)
        auc_scores["macro"] = auc_scores[f"class_{positive}"]
        auc_scores["micro"] = auc_scores[f"class_{positive}"]
        return curves, auc_scores

    for class_label in classes:
        binary_true = [1 if value == class_label else 0 for value in y_true]
        class_index = classes.index(class_label)
        scores = [row[class_index] for row in y_proba]
        if len(set(binary_true)) < 2:
            continue
        fpr, tpr, _ = roc_curve(binary_true, scores)
        score = auc(fpr, tpr)
        curves.append({
            "class_label": str(class_label),
            "fpr": [round(float(v), 6) for v in fpr],
            "tpr": [round(float(v), 6) for v in tpr],
            "auc": round(float(score), 4),
        })
        auc_scores[f"class_{class_label}"] = round(float(score), 4)

    if y_proba:
        try:
            auc_scores["macro"] = round(float(roc_auc_score(
                y_true, y_proba, multi_class="ovr", average="macro", labels=classes,
            )), 4)
            auc_scores["micro"] = round(float(roc_auc_score(
                y_true, y_proba, multi_class="ovr", average="micro", labels=classes,
            )), 4)
        except ValueError:
            auc_scores["macro"] = None
            auc_scores["micro"] = None

    return curves, auc_scores
