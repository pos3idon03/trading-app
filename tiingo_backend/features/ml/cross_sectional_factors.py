"""Rolling cross-sectional PCA/ICA factor features."""

from __future__ import annotations

from typing import Optional

import numpy as np
from sklearn.decomposition import PCA, FastICA


def _matrix_from_panel(
    log_returns: dict[str, list[float | None]],
    symbols: list[str],
    end_index: int,
    lookback: int,
) -> np.ndarray | None:
    start = max(1, end_index - lookback + 1)
    rows: list[list[float]] = []
    for i in range(start, end_index + 1):
        row: list[float] = []
        ok = True
        for sym in symbols:
            val = log_returns[sym][i]
            if val is None:
                ok = False
                break
            row.append(val)
        if ok:
            rows.append(row)
    if len(rows) < 2:
        return None
    return np.array(rows, dtype=float)


def fit_pca_loadings(
    matrix: np.ndarray,
    n_components: int = 3,
) -> np.ndarray:
    n_comp = min(n_components, matrix.shape[1], matrix.shape[0])
    if n_comp < 1:
        return np.zeros(matrix.shape[1])
    pca = PCA(n_components=n_comp)
    pca.fit(matrix)
    return pca.components_[0]


def fit_ica_loadings(
    matrix: np.ndarray,
    n_components: int = 3,
) -> np.ndarray:
    n_comp = min(n_components, matrix.shape[1], matrix.shape[0])
    if n_comp < 1:
        return np.zeros(matrix.shape[1])
    ica = FastICA(n_components=n_comp, random_state=42, max_iter=500)
    ica.fit(matrix)
    return ica.components_[0]


def build_factor_features_at_index(
    log_returns: dict[str, list[float | None]],
    symbols: list[str],
    index: int,
    *,
    lookback: int = 63,
    n_components: int = 3,
    use_ica: bool = False,
) -> dict[str, list[Optional[float]]]:
    matrix = _matrix_from_panel(log_returns, symbols, index, lookback)
    names = [
        "pca_factor_1_loading",
        "market_beta",
        "residual_vol",
    ]
    if matrix is None:
        return {sym: [None, None, None] for sym in symbols}

    loadings = (
        fit_ica_loadings(matrix, n_components)
        if use_ica
        else fit_pca_loadings(matrix, n_components)
    )
    market = matrix.mean(axis=1)
    market_std = float(np.std(market)) or 1e-9

    result: dict[str, list[Optional[float]]] = {}
    for i, sym in enumerate(symbols):
        loading = float(loadings[i]) if i < len(loadings) else 0.0
        sym_col = matrix[:, i]
        beta = float(np.corrcoef(sym_col, market)[0, 1]) if len(sym_col) > 1 else 0.0
        resid = float(np.std(sym_col - beta * market))
        result[sym] = [loading, beta, resid / market_std]
    return result


def factor_feature_names(use_ica: bool = False) -> list[str]:
    prefix = "ica" if use_ica else "pca"
    return [
        f"{prefix}_factor_1_loading",
        "market_beta",
        "residual_vol",
    ]
