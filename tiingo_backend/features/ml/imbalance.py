"""Class imbalance handling for ML training folds."""

from __future__ import annotations


def minority_class_ratio(y_train: list[int]) -> float:
    if not y_train:
        return 1.0
    counts: dict[int, int] = {}
    for label in y_train:
        counts[label] = counts.get(label, 0) + 1
    return min(counts.values()) / len(y_train)


def should_apply_smote(
    y_train: list[int],
    *,
    enabled: bool,
    min_ratio: float = 0.15,
) -> bool:
    if not enabled or len(y_train) < 6:
        return False
    return minority_class_ratio(y_train) < min_ratio


def maybe_smote(
    x_train: list[list[float]],
    y_train: list[int],
    *,
    enabled: bool = True,
    min_ratio: float = 0.15,
    model_type: str = "",
) -> tuple[list[list[float]], list[int]]:
    if model_type == "ml_lstm" or not should_apply_smote(
        y_train, enabled=enabled, min_ratio=min_ratio,
    ):
        return x_train, y_train

    try:
        from imblearn.over_sampling import SMOTE
    except ImportError:
        return x_train, y_train

    minority = min(sum(1 for y in y_train if y == label) for label in set(y_train))
    k = max(1, min(5, minority - 1))
    smote = SMOTE(random_state=42, k_neighbors=k)
    x_res, y_res = smote.fit_resample(x_train, y_train)
    return [list(row) for row in x_res], [int(v) for v in y_res]
