import numpy as np

from features.ml.price_features import FEATURE_NAMES
from features.ml.technical_pca import (
    fit_technical_pca,
    technical_column_indices,
    transform_rows_with_technical_pca,
)


def _synthetic_rows(count: int) -> tuple[list[str], list[list[float]]]:
    names = [*FEATURE_NAMES, "macro_level"]
    rows: list[list[float]] = []
    for index in range(count):
        price_block = [
            0.01 * (index % 5),
            0.02,
            0.03,
            0.015,
            50.0 + index * 0.1,
            0.01,
            0.02,
            0.005,
            0.012,
            0.015,
            0.02,
            0.03,
            0.001,
            0.0008,
            0.0002,
            0.55,
            0.04,
            0.1,
            0.01,
            0.008,
            1.05,
            0.002,
            0.004,
            1.2,
        ]
        rows.append([*price_block, float(index % 3)])
    return names, rows


def test_technical_column_indices_select_price_features_only():
    names, _ = _synthetic_rows(3)
    indices = technical_column_indices(names)
    assert indices == list(range(len(FEATURE_NAMES)))


def test_fit_technical_pca_reduces_dimensionality():
    names, rows = _synthetic_rows(40)
    state = fit_technical_pca(
        rows,
        names,
        variance_threshold=0.85,
        n_components=3,
    )
    assert state is not None
    assert state.n_components == 3
    assert len(state.output_names) == 4
    assert state.output_names[0].startswith("pc_tech_")

    transformed = transform_rows_with_technical_pca(rows[:5], state)
    assert len(transformed[0]) == 4


def test_transform_preserves_macro_columns():
    names, rows = _synthetic_rows(30)
    state = fit_technical_pca(rows, names, n_components=2)
    assert state is not None
    transformed = transform_rows_with_technical_pca(rows, state)
    macro_values = [row[-1] for row in transformed]
    assert macro_values == [row[-1] for row in rows]


def test_ewm_halflife_fit_does_not_crash():
    names, rows = _synthetic_rows(30)
    state = fit_technical_pca(rows, names, n_components=2, ewm_halflife=10.0)
    assert state is not None
    projected = transform_rows_with_technical_pca(rows, state)
    assert np.isfinite(projected[0][0])
