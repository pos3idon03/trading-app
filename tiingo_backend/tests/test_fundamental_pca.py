from features.ml.fundamental_pca import (
    fit_fundamental_pca,
    fundamental_column_indices,
    transform_rows_with_fundamental_pca,
)


def _feature_names():
    return [
        "ret_1",
        "revenue_level",
        "revenue_yoy",
        "revenue_qoq",
        "revenue_quarters_since_report",
        "roe_level",
        "grossMargin_level",
        "pe_ratio",
        "DFF_level",
    ]


def _rows(count: int):
    base = [0.01, 100.0, 0.05, 0.02, 1.0, 0.15, 0.35, 18.0, 4.5]
    return [base for _ in range(count)]


def test_kpi_only_column_selection():
    names = _feature_names()
    metrics = ["revenue", "roe", "grossMargin"]
    indices = fundamental_column_indices(
        names,
        fundamental_metrics=metrics,
        input_mode="kpi_only",
    )
    selected = [names[index] for index in indices]
    assert "revenue_level" not in selected
    assert "revenue_yoy" in selected
    assert "roe_level" in selected
    assert "pe_ratio" in selected
    assert "DFF_level" not in selected


def test_fundamental_pca_preserves_non_fundamental_columns():
    names = _feature_names()
    rows = _rows(30)
    params = {
        "feature_mode": "prices_macro_fundamentals",
        "fundamental_pca_enabled": True,
        "fundamental_pca_n_components": 2,
        "fundamental_metrics": ["revenue", "roe", "grossMargin"],
        "fundamental_pca_input_mode": "kpi_only",
    }
    state = fit_fundamental_pca(rows, names, params)
    assert state is not None
    transformed = transform_rows_with_fundamental_pca(rows[:2], state)
    assert state.output_names[0].startswith("pc_fund_")
    assert transformed[0][-1] == rows[0][-1]
