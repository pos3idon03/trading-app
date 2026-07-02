from features.ml.feature_preprocessor import fit_feature_preprocessor
from features.ml.price_features import FEATURE_NAMES


def _rows(count: int) -> list[list[float]]:
    base = [
        0.01,
        0.02,
        0.03,
        0.015,
        55.0,
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
    return [base for _ in range(count)]


def test_fit_feature_preprocessor_prunes_correlated_features():
    names = list(FEATURE_NAMES)
    rows = _rows(30)
    params = {"correlation_prune_threshold": 0.01}
    preprocessor = fit_feature_preprocessor(rows, [0, 1] * 15, names, params)
    transformed = preprocessor.transform(rows[:2])
    assert len(transformed[0]) <= len(names)
    assert preprocessor.pruned_features


def test_technical_pca_enabled_changes_output_names():
    names = list(FEATURE_NAMES)
    rows = _rows(40)
    params = {
        "technical_pca_enabled": True,
        "technical_pca_n_components": 3,
        "correlation_prune_threshold": 0.0,
    }
    preprocessor = fit_feature_preprocessor(rows, [0, 1] * 20, names, params)
    assert any(name.startswith("pc_tech_") for name in preprocessor.output_feature_names)
    assert len(preprocessor.transform(rows[:1])[0]) == len(preprocessor.output_feature_names)


def test_dynamic_indicator_selection_uses_model_importances():
    names = list(FEATURE_NAMES)
    rows = _rows(40)
    closes = [100.0 + index for index in range(40)]
    params = {
        "dynamic_indicator_selection": True,
        "correlation_prune_threshold": 0.0,
        "indicator_groups": ["momentum"],
    }
    preprocessor = fit_feature_preprocessor(
        rows,
        [index % 2 for index in range(40)],
        names,
        params,
        closes=closes,
        train_indices=list(range(40)),
    )
    assert preprocessor.regime_meta is not None
    assert preprocessor.regime_meta["selected"]


def test_chained_technical_and_fundamental_pca():
    from features.ml.price_features import FEATURE_NAMES

    names = [
        *FEATURE_NAMES,
        "revenue_yoy",
        "revenue_qoq",
        "roe_level",
        "pe_ratio",
    ]
    rows = []
    for row_index in range(40):
        row = [float(col_index) * 0.01 + row_index * 0.001 for col_index in range(len(names))]
        rows.append(row)
    params = {
        "technical_pca_enabled": True,
        "technical_pca_n_components": 3,
        "fundamental_pca_enabled": True,
        "fundamental_pca_n_components": 2,
        "feature_mode": "prices_macro_fundamentals",
        "fundamental_metrics": ["revenue", "roe"],
        "fundamental_pca_input_mode": "kpi_only",
        "correlation_prune_threshold": 0.0,
    }
    preprocessor = fit_feature_preprocessor(rows, [0, 1] * 20, names, params)
    assert any(name.startswith("pc_tech_") for name in preprocessor.output_feature_names)
    assert any(name.startswith("pc_fund_") for name in preprocessor.output_feature_names)
    assert len(preprocessor.transform(rows[:1])[0]) == len(preprocessor.output_feature_names)


def test_chained_technical_and_macro_category_pca():
    names = [
        *FEATURE_NAMES,
        "DFF_chg_1m",
        "DFF_chg_3m",
        "DGS10_chg_1m",
        "DGS10_chg_3m",
        "CPIAUCSL_chg_1m",
        "CPIAUCSL_chg_3m",
    ]
    rows = []
    for row_index in range(40):
        row = [float(col_index) * 0.01 + row_index * 0.001 for col_index in range(len(names))]
        rows.append(row)
    params = {
        "technical_pca_enabled": True,
        "technical_pca_n_components": 3,
        "macro_pca_enabled": True,
        "macro_pca_n_components": 1,
        "feature_mode": "prices_macro",
        "macro_series_ids": ["DFF", "DGS10", "CPIAUCSL"],
        "macro_pca_input_mode": "changes_only",
        "correlation_prune_threshold": 0.0,
    }
    preprocessor = fit_feature_preprocessor(rows, [0, 1] * 20, names, params)
    assert any(name.startswith("pc_tech_") for name in preprocessor.output_feature_names)
    assert any(name.startswith("pc_macro_rates_") for name in preprocessor.output_feature_names)
    assert any(name.startswith("pc_macro_inflation_") for name in preprocessor.output_feature_names)


def test_chained_pca_preserves_fundamental_passthrough_values():
    names = [
        *FEATURE_NAMES,
        "revenue_yoy",
        "revenue_qoq",
        "revenue_quarters_since_report",
        "roe_level",
        "pe_ratio",
    ]
    rows = []
    for row_index in range(40):
        row = [float(col_index) * 0.01 + row_index * 0.001 for col_index in range(len(names))]
        rows.append(row)
    params = {
        "technical_pca_enabled": True,
        "technical_pca_n_components": 3,
        "fundamental_pca_enabled": True,
        "fundamental_pca_n_components": 2,
        "feature_mode": "prices_macro_fundamentals",
        "fundamental_metrics": ["revenue", "roe"],
        "fundamental_pca_input_mode": "kpi_only",
        "correlation_prune_threshold": 0.0,
    }
    preprocessor = fit_feature_preprocessor(rows, [0, 1] * 20, names, params)
    pe_index = names.index("revenue_quarters_since_report")
    transformed = preprocessor.transform(rows[:1])[0]
    assert "revenue_quarters_since_report" in preprocessor.output_feature_names
    assert (
        transformed[preprocessor.output_feature_names.index("revenue_quarters_since_report")]
        == rows[0][pe_index]
    )
