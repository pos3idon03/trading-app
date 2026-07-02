"""Shared walk-forward PCA for a single feature block."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def block_pca_output_names(prefix: str, n_components: int) -> list[str]:
    return [f"{prefix}_{index + 1}" for index in range(n_components)]


def ewm_sample_weights(row_count: int, halflife: float) -> np.ndarray:
    ages = np.arange(row_count - 1, -1, -1, dtype=float)
    decay = np.log(2.0) / max(halflife, 1.0)
    weights = np.exp(-decay * ages)
    total = weights.sum()
    if total <= 0:
        return np.ones(row_count) / row_count
    return weights / total


def resolve_n_components(
    pca: PCA,
    *,
    variance_threshold: float,
    fixed_components: int | None,
) -> int:
    if fixed_components is not None and fixed_components > 0:
        return min(fixed_components, pca.components_.shape[0])
    cumulative = np.cumsum(pca.explained_variance_ratio_)
    for index, ratio in enumerate(cumulative, start=1):
        if ratio >= variance_threshold:
            return index
    return len(cumulative)


@dataclass
class BlockPcaState:
    source_indices: list[int]
    passthrough_indices: list[int]
    n_components: int
    scaler: StandardScaler
    pca: PCA
    output_names: list[str]


def fit_pca_matrix(
    scaled: np.ndarray,
    n_components: int,
    sample_weight: np.ndarray | None = None,
) -> PCA:
    n_comp = min(n_components, scaled.shape[1], scaled.shape[0])
    if sample_weight is None:
        pca = PCA(n_components=n_comp)
        pca.fit(scaled)
        return pca

    weights = sample_weight / sample_weight.sum()
    mean = np.average(scaled, axis=0, weights=weights)
    centered = scaled - mean
    covariance = centered.T @ (centered * weights[:, None])
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    components = eigenvectors[:, order[:n_comp]].T
    explained = eigenvalues[order[:n_comp]]
    total_variance = float(explained.sum()) or 1.0

    pca = PCA(n_components=n_comp)
    pca.components_ = components
    pca.explained_variance_ = explained
    pca.explained_variance_ratio_ = explained / total_variance
    pca.mean_ = mean
    pca.n_features_in_ = scaled.shape[1]
    pca.n_components_ = n_comp
    return pca


def fit_block_pca(
    x_train: list[list[float]],
    feature_names: list[str],
    source_indices: list[int],
    *,
    output_prefix: str,
    variance_threshold: float = 0.85,
    n_components: int | None = None,
    ewm_halflife: float | None = None,
) -> Optional[BlockPcaState]:
    if len(source_indices) < 2 or len(x_train) < 2:
        return None

    matrix = np.array([[row[index] for index in source_indices] for row in x_train], dtype=float)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(matrix)

    max_components = min(len(source_indices), len(x_train))
    sample_weight = None
    if ewm_halflife is not None and ewm_halflife > 0:
        sample_weight = ewm_sample_weights(len(x_train), ewm_halflife)

    probe = fit_pca_matrix(scaled, max_components, sample_weight)
    resolved = resolve_n_components(
        probe,
        variance_threshold=variance_threshold,
        fixed_components=n_components,
    )
    if resolved < 1:
        return None

    pca = fit_pca_matrix(scaled, resolved, sample_weight)
    source_set = set(source_indices)
    passthrough = [index for index in range(len(feature_names)) if index not in source_set]
    pc_names = block_pca_output_names(output_prefix, resolved)
    passthrough_names = [feature_names[index] for index in passthrough]
    return BlockPcaState(
        source_indices=source_indices,
        passthrough_indices=passthrough,
        n_components=resolved,
        scaler=scaler,
        pca=pca,
        output_names=[*pc_names, *passthrough_names],
    )


def block_pcas_output_names(
    feature_names: list[str],
    states: list[BlockPcaState],
) -> list[str]:
    if not states:
        return list(feature_names)

    all_sources: set[int] = set()
    pc_names: list[str] = []
    for state in states:
        overlap = all_sources.intersection(state.source_indices)
        if overlap:
            raise ValueError(f"Overlapping block PCA source indices: {sorted(overlap)}")
        all_sources.update(state.source_indices)
        pc_names.extend(state.output_names[: state.n_components])

    passthrough = [feature_names[index] for index in range(len(feature_names)) if index not in all_sources]
    return [*pc_names, *passthrough]


def transform_rows_with_block_pca(
    rows: list[list[float]],
    state: BlockPcaState,
) -> list[list[float]]:
    return transform_rows_with_block_pcas(rows, [state])


def transform_rows_with_block_pcas(
    rows: list[list[float]],
    states: list[BlockPcaState],
) -> list[list[float]]:
    if not rows:
        return []
    active = [state for state in states if state is not None]
    if not active:
        return rows

    all_sources: set[int] = set()
    for state in active:
        overlap = all_sources.intersection(state.source_indices)
        if overlap:
            raise ValueError(f"Overlapping block PCA source indices: {sorted(overlap)}")
        all_sources.update(state.source_indices)

    n_features = len(rows[0])
    passthrough_indices = [index for index in range(n_features) if index not in all_sources]
    transformed: list[list[float]] = []

    for row in rows:
        pc_values: list[float] = []
        for state in active:
            source_matrix = np.array(
                [[row[index] for index in state.source_indices]],
                dtype=float,
            )
            projected = state.pca.transform(state.scaler.transform(source_matrix))[0]
            pc_values.extend(projected.tolist())
        passthrough = [row[index] for index in passthrough_indices]
        transformed.append([*pc_values, *passthrough])

    return transformed


def fit_block_pca_by_indices(
    x_train: list[list[float]],
    feature_names: list[str],
    index_resolver: Callable[[list[str]], list[int]],
    *,
    output_prefix: str,
    variance_threshold: float = 0.85,
    n_components: int | None = None,
    ewm_halflife: float | None = None,
) -> Optional[BlockPcaState]:
    indices = index_resolver(feature_names)
    return fit_block_pca(
        x_train,
        feature_names,
        indices,
        output_prefix=output_prefix,
        variance_threshold=variance_threshold,
        n_components=n_components,
        ewm_halflife=ewm_halflife,
    )
