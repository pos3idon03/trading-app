from features.ml.label_search import run_label_grid_search, run_multi_model_label_grid_search


def _bars(closes: list[float]) -> list[dict]:
    return [{"close": price} for price in closes]


def _feature_rows(count: int) -> list[list[float]]:
    return [[float(index), float(index) * 0.1] for index in range(count)]


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
