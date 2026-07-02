"""Walk-forward PCA on price/technical feature columns only."""

from __future__ import annotations

from typing import Optional

from features.ml.block_pca import (
    BlockPcaState,
    fit_block_pca_by_indices,
    transform_rows_with_block_pca,
)
from features.ml.price_features import FEATURE_NAMES

PRICE_TECHNICAL_NAMES = frozenset(FEATURE_NAMES)
TechnicalPcaState = BlockPcaState


def technical_column_indices(feature_names: list[str]) -> list[int]:
    return [index for index, name in enumerate(feature_names) if name in PRICE_TECHNICAL_NAMES]


def technical_pca_output_names(n_components: int) -> list[str]:
    return [f"pc_tech_{index + 1}" for index in range(n_components)]


def fit_technical_pca(
    x_train: list[list[float]],
    feature_names: list[str],
    *,
    variance_threshold: float = 0.85,
    n_components: int | None = None,
    ewm_halflife: float | None = None,
) -> Optional[BlockPcaState]:
    return fit_block_pca_by_indices(
        x_train,
        feature_names,
        technical_column_indices,
        output_prefix="pc_tech",
        variance_threshold=variance_threshold,
        n_components=n_components,
        ewm_halflife=ewm_halflife,
    )


def transform_rows_with_technical_pca(
    rows: list[list[float]],
    state: BlockPcaState,
) -> list[list[float]]:
    return transform_rows_with_block_pca(rows, state)
