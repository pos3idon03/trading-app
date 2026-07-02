"""Pearson correlation-based feature pruning for walk-forward folds."""

from __future__ import annotations

import math


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n < 2:
        return 0.0
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    num = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    den_a = math.sqrt(sum((x - mean_a) ** 2 for x in a))
    den_b = math.sqrt(sum((y - mean_b) ** 2 for y in b))
    if den_a == 0 or den_b == 0:
        return 0.0
    return num / (den_a * den_b)


def prune_correlated_features(
    x_train: list[list[float]],
    feature_names: list[str],
    *,
    threshold: float = 0.75,
) -> tuple[list[int], list[str]]:
    if threshold <= 0 or not x_train:
        indices = list(range(len(feature_names)))
        return indices, []

    if not feature_names:
        feature_names = [f"f{i}" for i in range(len(x_train[0]))]

    row_width = min(len(row) for row in x_train)
    if len(feature_names) > row_width:
        feature_names = feature_names[:row_width]

    n_features = len(feature_names)
    keep = [True] * n_features
    pruned: list[str] = []

    for i in range(n_features):
        if not keep[i]:
            continue
        col_i = [row[i] for row in x_train]
        for j in range(i + 1, n_features):
            if not keep[j]:
                continue
            col_j = [row[j] for row in x_train]
            corr = abs(_pearson(col_i, col_j))
            if corr > threshold:
                keep[j] = False
                pruned.append(feature_names[j])

    kept_indices = [idx for idx, flag in enumerate(keep) if flag]
    return kept_indices, pruned


def apply_feature_mask(
    rows: list[list[float]],
    mask: list[int],
) -> list[list[float]]:
    return [[row[i] for i in mask] for row in rows]


def mask_feature_names(
    feature_names: list[str],
    mask: list[int],
) -> list[str]:
    return [feature_names[i] for i in mask]
