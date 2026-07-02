from features.ml.catalog import (
    DEFAULT_LABEL_MODE_BY_MODEL,
    default_label_mode_for_model,
    validate_model_label_search_configs,
)
from features.ml.label_search import (
    label_search_work_units,
    run_label_grid_search,
    run_multi_model_label_grid_search,
)
from features.ml.orchestrator import _label_search_total_work, _resolve_label_search_configs
from features.ml.price_features import build_price_feature_matrix


def _bars(closes: list[float]) -> list[dict]:
    return [{"close": price} for price in closes]


def _feature_rows(count: int) -> list[list[float]]:
    return [[float(index), float(index) * 0.1] for index in range(count)]


def test_label_grid_search_with_price_feature_warmup():
    bars = _bars([100 + index for index in range(500)])
    for bar in bars:
        bar.update({"high": bar["close"] + 1, "low": bar["close"] - 1, "volume": 1000})
    feature_names, feature_rows = build_price_feature_matrix(bars)

    rows = run_label_grid_search(
        bars=bars,
        feature_rows=feature_rows,
        feature_names=feature_names,
        label_mode="binary",
        horizons=[5],
        thresholds=[0.01],
        train_bars=252,
        test_bars=63,
        step_bars=63,
        model_type="ml_logistic",
    )

    assert len(rows) == 1
    assert rows[0]["oos_window_count"] is not None
    assert rows[0]["oos_window_count"] >= 1


def test_run_label_grid_search_includes_model_metadata():
    bars = _bars([100 + index for index in range(40)])
    rows = run_label_grid_search(
        bars=bars,
        feature_rows=_feature_rows(len(bars)),
        label_mode="binary",
        horizons=[2],
        thresholds=[0.01],
        train_bars=10,
        test_bars=5,
        step_bars=5,
        model_type="ml_logistic",
    )

    assert len(rows) == 1
    assert rows[0]["model_type"] == "ml_logistic"
    assert rows[0]["model_label"] == "Logistic Regression"
    assert rows[0]["label_key"].startswith("ml_logistic_")


def test_run_multi_model_label_grid_search_covers_all_models():
    bars = _bars([100 + index for index in range(40)])
    rows = run_multi_model_label_grid_search(
        bars=bars,
        feature_rows=_feature_rows(len(bars)),
        label_mode="binary",
        horizons=[2, 4],
        thresholds=[0.01],
        train_bars=10,
        test_bars=5,
        step_bars=5,
        model_types=["ml_logistic", "ml_knn"],
    )

    assert len(rows) == 4
    model_types = {row["model_type"] for row in rows}
    assert model_types == {"ml_logistic", "ml_knn"}


def test_run_multi_model_label_grid_search_sorts_by_f1_macro():
    bars = _bars([100 + index for index in range(40)])
    rows = run_multi_model_label_grid_search(
        bars=bars,
        feature_rows=_feature_rows(len(bars)),
        label_mode="binary",
        horizons=[2],
        thresholds=[0.01],
        train_bars=10,
        test_bars=5,
        step_bars=5,
        model_types=["ml_logistic", "ml_knn"],
    )

    scores = [row["f1_macro"] for row in rows if row["f1_macro"] is not None]
    assert scores == sorted(scores, reverse=True)


def test_label_grid_search_knn_with_sparse_folds():
    bar_count = 250
    bars = _bars([100 + index for index in range(bar_count)])
    feature_rows: list[list[float] | None] = [None] * bar_count
    for index in range(147, bar_count):
        feature_rows[index] = [float(index), float(index) * 0.1]

    rows = run_label_grid_search(
        bars=bars,
        feature_rows=feature_rows,
        label_mode="binary",
        horizons=[2],
        thresholds=[0.01],
        train_bars=150,
        test_bars=50,
        step_bars=50,
        model_type="ml_knn",
    )

    assert len(rows) == 1
    assert rows[0]["model_type"] == "ml_knn"
    assert rows[0]["oos_window_count"] is not None
    assert rows[0]["oos_window_count"] >= 1


def test_default_label_mode_by_model_matches_catalog():
    assert default_label_mode_for_model("ml_logistic") == "binary"
    assert default_label_mode_for_model("ml_lstm") == "meta_label"
    assert default_label_mode_for_model("ml_random_forest") == "ternary"
    assert set(DEFAULT_LABEL_MODE_BY_MODEL) == {
        "ml_logistic",
        "ml_random_forest",
        "ml_gradient_boosting",
        "ml_xgboost",
        "ml_knn",
        "ml_lstm",
    }


def test_validate_model_label_search_configs():
    configs = validate_model_label_search_configs([
        {"model_type": "ml_logistic", "label_mode": "binary"},
        {"model_type": "ml_lstm", "label_mode": "meta_label"},
    ])
    assert configs == [("ml_logistic", "binary"), ("ml_lstm", "meta_label")]


def test_resolve_label_search_configs_prefers_model_configs():
    resolved = _resolve_label_search_configs(
        model_configs=[
            {"model_type": "ml_logistic", "label_mode": "binary"},
            {"model_type": "ml_lstm", "label_mode": "meta_label"},
        ],
        model_type=None,
        model_types=["ml_knn"],
        label_mode="ternary",
    )
    assert resolved == [("ml_logistic", "binary"), ("ml_lstm", "meta_label")]


def test_resolve_label_search_configs_legacy_fallback():
    resolved = _resolve_label_search_configs(
        model_configs=None,
        model_type="ml_knn",
        model_types=None,
        label_mode="binary",
    )
    assert resolved == [("ml_knn", "binary")]


def test_label_search_work_units_meta_label_single_combo():
    horizons = [1, 3, 5, 7, 9]
    units = label_search_work_units("meta_label", horizons, [0.01, 0.02])
    assert len(units) == 1
    binary_units = label_search_work_units("binary", horizons, [0.01])
    assert len(binary_units) == len(horizons)


def test_label_search_total_work_accounts_for_meta_label():
    configs = [("ml_logistic", "binary"), ("ml_lstm", "meta_label")]
    horizons = [1, 3, 5]
    total = _label_search_total_work(configs, horizons, [0.01])
    assert total == len(horizons) + 1
