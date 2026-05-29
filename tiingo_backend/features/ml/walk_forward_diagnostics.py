from typing import Any, Optional

from features.ml.labels import build_labels_for_ml_params
from features.ml.price_features import FEATURE_WARMUP_BARS
from features.ml.splitter import build_walk_forward_windows


def count_valid_feature_rows(feature_rows: list[Optional[list[float]]]) -> int:
    return sum(1 for row in feature_rows if row is not None)


def count_labeled_rows(labels: list[Optional[int]]) -> int:
    return sum(1 for label in labels if label is not None)


def count_trainable_rows(
    feature_rows: list[Optional[list[float]]],
    labels: list[Optional[int]],
) -> int:
    return sum(
        1
        for features, label in zip(feature_rows, labels)
        if features is not None and label is not None
    )


def _collect_samples(
    indices: list[int],
    feature_rows: list[Optional[list[float]]],
    labels: list[Optional[int]],
) -> tuple[list[list[float]], list[int]]:
    x_rows: list[list[float]] = []
    y_rows: list[int] = []
    for index in indices:
        features = feature_rows[index]
        label = labels[index]
        if features is None or label is None:
            continue
        x_rows.append(features)
        y_rows.append(label)
    return x_rows, y_rows


def count_structural_walk_forward_folds(
    bar_count: int,
    train_bars: int,
    test_bars: int,
    step_bars: int,
) -> int:
    if bar_count < train_bars + test_bars:
        return 0
    try:
        return len(build_walk_forward_windows(bar_count, train_bars, test_bars, step_bars))
    except ValueError:
        return 0


def count_viable_walk_forward_folds(
    feature_rows: list[Optional[list[float]]],
    labels: list[Optional[int]],
    train_bars: int,
    test_bars: int,
    step_bars: int,
) -> int:
    bar_count = len(feature_rows)
    if bar_count < train_bars + test_bars:
        return 0

    try:
        windows = build_walk_forward_windows(bar_count, train_bars, test_bars, step_bars)
    except ValueError:
        return 0

    viable = 0
    for train_indices, test_indices in windows:
        x_train, y_train = _collect_samples(train_indices, feature_rows, labels)
        x_test, _ = _collect_samples(test_indices, feature_rows, labels)
        if len(x_train) < 2 or len(set(y_train)) < 2 or not x_test:
            continue
        viable += 1
    return viable


def _append_readiness_issues(
    issues: list[str],
    *,
    total_bars: int,
    valid_feature_rows: int,
    labeled_rows: int,
    trainable_rows: int,
    structural_folds: int,
    viable_folds: int,
    train_bars: int,
    validated_params: dict,
) -> None:
    if valid_feature_rows == 0:
        issues.append(
            "No valid feature rows — optional context/strategy features or macro "
            "coverage may have nullified all rows.",
        )
    elif trainable_rows == 0 and labeled_rows > 0:
        issues.append(
            "Labels exist but no bars have both features and labels for training.",
        )

    if viable_folds == 0 and labeled_rows > 0:
        if structural_folds == 0:
            issues.append(
                "Date range is too short for the walk-forward train + test windows.",
            )
        else:
            issues.append(
                "Walk-forward folds exist structurally but none can train — "
                "increase train_bars above warmup, extend the date range, or "
                "include more varied market history.",
            )

    if train_bars <= FEATURE_WARMUP_BARS:
        issues.append(
            f"Train bars ({train_bars}) is at or below the {FEATURE_WARMUP_BARS}-bar "
            "feature warmup — most training windows lack usable features.",
        )

    context_tfs = validated_params.get("context_timeframes") or []
    strategy_ids = validated_params.get("strategy_feature_ids") or []
    if (context_tfs or strategy_ids) and valid_feature_rows < max(1, total_bars // 4):
        issues.append(
            "Optional context or strategy features are enabled but most bars lack "
            "merged features — try unchecking them on Data Prep.",
        )


def build_walk_forward_readiness(
    bars: list[dict],
    feature_rows: list[Optional[list[float]]],
    validated_params: dict,
) -> dict[str, Any]:
    train_bars = int(validated_params["train_bars"])
    test_bars = int(validated_params["test_bars"])
    step_bars = int(validated_params["step_bars"])
    label_horizon = int(validated_params["label_horizon"])

    labels = build_labels_for_ml_params(bars, validated_params)

    total_bars = len(bars)
    valid_feature_rows = count_valid_feature_rows(feature_rows)
    labeled_rows = count_labeled_rows(labels)
    trainable_rows = count_trainable_rows(feature_rows, labels)
    structural_folds = count_structural_walk_forward_folds(
        len(feature_rows),
        train_bars,
        test_bars,
        step_bars,
    )
    viable_folds = count_viable_walk_forward_folds(
        feature_rows,
        labels,
        train_bars,
        test_bars,
        step_bars,
    )

    readiness_issues: list[str] = []
    _append_readiness_issues(
        readiness_issues,
        total_bars=total_bars,
        valid_feature_rows=valid_feature_rows,
        labeled_rows=labeled_rows,
        trainable_rows=trainable_rows,
        structural_folds=structural_folds,
        viable_folds=viable_folds,
        train_bars=train_bars,
        validated_params=validated_params,
    )

    return {
        "total_bars": total_bars,
        "warmup_bars": FEATURE_WARMUP_BARS,
        "valid_feature_rows": valid_feature_rows,
        "labeled_rows": labeled_rows,
        "trainable_rows": trainable_rows,
        "structural_folds": structural_folds,
        "viable_folds": viable_folds,
        "train_bars": train_bars,
        "test_bars": test_bars,
        "step_bars": step_bars,
        "label_horizon": label_horizon,
        "readiness_issues": readiness_issues,
    }
