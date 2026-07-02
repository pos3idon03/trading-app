from features.ml.macro_pca import (
    fit_macro_pca,
    macro_columns_by_category,
    transform_rows_with_macro_pca,
)


def _macro_feature_names():
    return [
        "ret_1",
        "DFF_chg_1m",
        "DFF_chg_3m",
        "DGS10_chg_1m",
        "DGS10_chg_3m",
        "CPIAUCSL_chg_1m",
        "CPIAUCSL_chg_3m",
        "UNRATE_level",
        "UNRATE_chg_1m",
    ]


def _rows(count: int):
    base = [0.01, 0.02, 0.03, 0.025, 0.035, 0.01, 0.015, 4.5, 0.001]
    return [base for _ in range(count)]


def test_changes_only_column_selection():
    names = _macro_feature_names()
    by_category = macro_columns_by_category(
        names,
        ["DFF", "DGS10", "CPIAUCSL", "UNRATE"],
        input_mode="changes_only",
    )
    rates = [names[index] for index in by_category["rates"]]
    inflation = [names[index] for index in by_category["inflation"]]
    labor = [names[index] for index in by_category["labor"]]

    assert "DFF_chg_1m" in rates
    assert "DGS10_chg_3m" in rates
    assert "CPIAUCSL_chg_1m" in inflation
    assert "UNRATE_level" not in labor
    assert "UNRATE_chg_1m" in labor


def test_all_macro_excludes_days_since_update():
    names = ["DFF_level", "DFF_days_since_update", "DFF_chg_1m"]
    by_category = macro_columns_by_category(names, ["DFF"], input_mode="all_macro")
    selected = [names[index] for index in by_category["rates"]]
    assert "DFF_level" in selected
    assert "DFF_chg_1m" in selected
    assert "DFF_days_since_update" not in selected


def test_single_column_category_skipped():
    names = ["ret_1", "CPIAUCSL_chg_1m"]
    rows = _rows(30)
    params = {
        "feature_mode": "prices_macro",
        "macro_pca_enabled": True,
        "macro_pca_n_components": 1,
        "macro_series_ids": ["CPIAUCSL"],
        "macro_pca_input_mode": "changes_only",
    }
    bundle = fit_macro_pca(rows, names, params)
    assert bundle is None


def test_category_macro_pca_output_prefixes():
    names = _macro_feature_names()
    rows = _rows(40)
    params = {
        "feature_mode": "prices_macro",
        "macro_pca_enabled": True,
        "macro_pca_n_components": 1,
        "macro_series_ids": ["DFF", "DGS10", "CPIAUCSL", "UNRATE"],
        "macro_pca_input_mode": "changes_only",
    }
    bundle = fit_macro_pca(rows, names, params)
    assert bundle is not None
    assert "rates" in bundle.states
    assert bundle.states["rates"].output_names[0].startswith("pc_macro_rates_")
    transformed = transform_rows_with_macro_pca(rows[:2], bundle)
    ret_index = bundle.output_names.index("ret_1")
    assert transformed[0][ret_index] == rows[0][0]
