"""Lopez de Prado hierarchical risk parity (recursive bisection)."""

from __future__ import annotations

import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform


def correlation_distance(corr: np.ndarray) -> np.ndarray:
    dist = np.sqrt(0.5 * (1.0 - corr))
    np.fill_diagonal(dist, 0.0)
    return dist


def quasi_diag(link: np.ndarray) -> list[int]:
    return leaves_list(link).tolist()


def cluster_variance(cov: np.ndarray, indices: list[int]) -> float:
    sub = cov[np.ix_(indices, indices)]
    if sub.size == 0:
        return 0.0
    w = np.ones(len(indices)) / len(indices)
    return float(w @ sub @ w)


def recursive_bisection(cov: np.ndarray, ordered: list[int]) -> np.ndarray:
    n = len(ordered)
    weights = np.ones(n)
    clusters = [ordered]

    while clusters:
        next_clusters: list[list[int]] = []
        for cluster in clusters:
            if len(cluster) <= 1:
                continue
            mid = len(cluster) // 2
            left, right = cluster[:mid], cluster[mid:]
            v_left = cluster_variance(cov, left)
            v_right = cluster_variance(cov, right)
            total = v_left + v_right
            alpha = 0.5 if total <= 0 else 1.0 - v_left / total
            for i in left:
                weights[ordered.index(i)] *= alpha
            for i in right:
                weights[ordered.index(i)] *= 1.0 - alpha
            if len(left) > 1:
                next_clusters.append(left)
            if len(right) > 1:
                next_clusters.append(right)
        clusters = next_clusters

    total_w = weights.sum()
    if total_w <= 0:
        return np.ones(n) / n
    return weights / total_w


def compute_hrp_weights(
    returns_matrix: list[list[float]],
    *,
    linkage_method: str = "single",
) -> dict[int, float]:
    """returns_matrix: rows=time, cols=assets. Returns index->weight."""
    if not returns_matrix:
        return {}
    arr = np.array(returns_matrix, dtype=float)
    if arr.shape[0] < 2 or arr.shape[1] < 1:
        n = arr.shape[1] if arr.ndim > 1 else 1
        return {i: 1.0 / n for i in range(n)}

    corr = np.corrcoef(arr, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)
    dist = correlation_distance(corr)
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method=linkage_method)
    ordered = quasi_diag(link)
    cov = np.cov(arr, rowvar=False)
    if cov.ndim == 0:
        return {0: 1.0}
    w = recursive_bisection(cov, ordered)
    return {ordered[i]: float(w[i]) for i in range(len(ordered))}


def weights_for_symbols(
    returns_matrix: list[list[float]],
    symbols: list[str],
    *,
    linkage_method: str = "single",
) -> dict[str, float]:
    idx_weights = compute_hrp_weights(returns_matrix, linkage_method=linkage_method)
    return {
        symbols[i]: idx_weights.get(i, 0.0)
        for i in range(len(symbols))
    }
