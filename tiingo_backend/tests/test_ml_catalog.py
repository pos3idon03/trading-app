import pytest

from features.ml.catalog import (
    default_walk_forward_params,
    feature_mode_uses_macro,
    minimum_bars_required,
    validate_ml_params,
)


def test_validate_ml_params_rejects_invalid_inference_eval_scope():
    with pytest.raises(ValueError, match="inference_eval_scope"):
        validate_ml_params("ml_logistic", {"inference_eval_scope": "invalid"})


def test_validate_ml_params_rejects_invalid_correlation_prune_threshold():
    with pytest.raises(ValueError, match="correlation_prune_threshold"):
        validate_ml_params("ml_logistic", {"correlation_prune_threshold": 1.5})


def test_validate_ml_params_defaults_inference_eval_scope():
    params = validate_ml_params("ml_logistic", {"feature_mode": "prices_only"})
    assert params["inference_eval_scope"] == "holdout"


def test_validate_ml_params_defaults_exit_policy_binary():
    params = validate_ml_params("ml_logistic", {"feature_mode": "prices_only"})
    assert params["exit_policy"] == "label_horizon"


def test_validate_ml_params_defaults_exit_policy_meta_label():
    params = validate_ml_params(
        "ml_logistic",
        {"feature_mode": "prices_only", "label_mode": "meta_label"},
    )
    assert params["exit_policy"] == "atr_bracket"


def test_validate_ml_params_accepts_include_news_sentiment():
    params = validate_ml_params(
        "ml_logistic",
        {"feature_mode": "prices_only", "include_news_sentiment": True},
    )
    assert params["include_news_sentiment"] is True


def test_validate_ml_params_rejects_unknown_feature_mode():
    with pytest.raises(ValueError, match="Unsupported feature_mode"):
        validate_ml_params("ml_logistic", {"feature_mode": "prices_only_macro"})


def test_validate_ml_params_accepts_prices_macro_fundamentals():
    params = validate_ml_params(
        "ml_logistic",
        {
            "feature_mode": "prices_macro_fundamentals",
            "macro_series_ids": ["DFF", "CPIAUCSL"],
            "fundamental_metrics": ["revenue", "roe"],
            "fundamental_period_type": "quarterly",
        },
    )
    assert params["feature_mode"] == "prices_macro_fundamentals"
    assert params["fundamental_metrics"] == ["revenue", "roe"]


def test_validate_ml_params_rejects_empty_fundamental_metrics():
    with pytest.raises(ValueError, match="fundamental_metrics"):
        validate_ml_params(
            "ml_logistic",
            {
                "feature_mode": "prices_macro_fundamentals",
                "macro_series_ids": ["DFF"],
                "fundamental_metrics": [],
            },
        )


def test_validate_ml_params_rejects_unknown_fundamental_metric():
    with pytest.raises(ValueError, match="Unknown fundamental metric"):
        validate_ml_params(
            "ml_logistic",
            {
                "feature_mode": "prices_macro_fundamentals",
                "macro_series_ids": ["DFF"],
                "fundamental_metrics": ["not_a_metric"],
            },
        )


def test_validate_ml_params_accepts_prices_macro_with_series_ids():
    params = validate_ml_params(
        "ml_logistic",
        {"feature_mode": "prices_macro", "macro_series_ids": ["DFF", "CPIAUCSL"]},
    )
    assert params["feature_mode"] == "prices_macro"
    assert params["macro_series_ids"] == ["DFF", "CPIAUCSL"]


def test_validate_ml_params_rejects_empty_macro_series_ids():
    with pytest.raises(ValueError, match="macro_series_ids"):
        validate_ml_params(
            "ml_logistic",
            {"feature_mode": "prices_macro", "macro_series_ids": []},
        )


def test_validate_ml_params_accepts_new_noise_reduction_params():
    params = validate_ml_params(
        "ml_logistic",
        {
            "train_bars": 300,
            "technical_pca_enabled": True,
            "technical_pca_variance_threshold": 0.9,
            "macro_features_mode": "changes_only",
            "lstm_early_stopping_patience": 5,
        },
    )
    assert params["technical_pca_enabled"] is True
    assert params["macro_features_mode"] == "changes_only"
    assert params["lstm_early_stopping_patience"] == 5


def test_validate_ml_params_merges_defaults():
    params = validate_ml_params("ml_logistic", {"train_bars": 120, "warmup_bars": 100})
    assert params["train_bars"] == 120
    assert params["feature_mode"] == "prices_only"


def test_validate_ml_params_accepts_train_bars_of_10():
    params = validate_ml_params(
        "ml_logistic",
        {"train_bars": 60, "test_bars": 20, "warmup_bars": 50},
    )
    assert params["train_bars"] == 60
    assert params["test_bars"] == 20


def test_validate_ml_params_rejects_train_bars_below_minimum():
    with pytest.raises(ValueError, match="train_bars"):
        validate_ml_params("ml_logistic", {"train_bars": 9})


def test_validate_ml_params_applies_timeframe_defaults():
    daily = validate_ml_params("ml_logistic", {}, timeframe="1d")
    hourly = validate_ml_params("ml_logistic", {}, timeframe="1h")
    assert daily["train_bars"] == 252
    assert hourly["train_bars"] > daily["train_bars"]
    assert hourly["test_bars"] > daily["test_bars"]


def test_default_walk_forward_params_weekly():
    params = default_walk_forward_params("1w")
    assert params["train_bars"] == 52
    assert params["test_bars"] == 13
    assert params["label_horizon"] == 4


def test_minimum_bars_differs_by_timeframe_defaults():
    daily_params = validate_ml_params("ml_logistic", {}, timeframe="1d")
    hourly_params = validate_ml_params("ml_logistic", {}, timeframe="1h")
    assert minimum_bars_required(hourly_params) > minimum_bars_required(daily_params)


def test_minimum_bars_for_inference_uses_warmup_not_train_window():
    from features.ml.catalog import minimum_bars_for_inference
    from features.ml.price_features import FEATURE_WARMUP_BARS

    hourly_params = validate_ml_params("ml_logistic", {}, timeframe="1h")
    assert minimum_bars_for_inference(hourly_params) == FEATURE_WARMUP_BARS + 1
    assert minimum_bars_for_inference(hourly_params) < minimum_bars_required(hourly_params)


def test_validate_warmup_bars_custom():
    params = validate_ml_params("ml_logistic", {"warmup_bars": 150})
    assert params["warmup_bars"] == 150


def test_validate_warmup_bars_rejects_train_at_or_below_warmup():
    import pytest

    with pytest.raises(ValueError, match="train_bars"):
        validate_ml_params("ml_logistic", {"warmup_bars": 300, "train_bars": 252})


def test_minimum_bars_required_uses_custom_warmup():
    params = validate_ml_params("ml_logistic", {"warmup_bars": 100})
    assert minimum_bars_required(params) == 100 + params["train_bars"] + params["test_bars"] + params["label_horizon"]


def test_validate_ml_params_accepts_gradient_boosting_hyperparam():
    params = validate_ml_params(
        "ml_gradient_boosting",
        {"gradient_boosting_max_iter": 150},
    )
    assert params["gradient_boosting_max_iter"] == 150


def test_list_ml_models_exposes_hyperparameter_support_flags():
    from features.ml.catalog import list_ml_models

    models = {row["id"]: row for row in list_ml_models()}
    assert models["ml_logistic"]["supports_hyperparameter_search"] is False
    assert models["ml_random_forest"]["supports_hyperparameter_search"] is True


def test_feature_mode_uses_macro():
    assert feature_mode_uses_macro("prices_macro") is True
    assert feature_mode_uses_macro("prices_macro_fundamentals") is True
    assert feature_mode_uses_macro("prices_only") is False


def test_validate_ml_params_accepts_fundamental_pca_params():
    params = validate_ml_params(
        "ml_logistic",
        {
            "train_bars": 300,
            "feature_mode": "prices_macro_fundamentals",
            "fundamental_metrics": ["revenue", "roe"],
            "fundamental_pca_enabled": True,
            "fundamental_features_mode": "growth_only",
            "fundamental_pca_input_mode": "kpi_only",
        },
    )
    assert params["fundamental_pca_enabled"] is True
    assert params["fundamental_features_mode"] == "growth_only"


def test_validate_ml_params_accepts_macro_pca_params():
    params = validate_ml_params(
        "ml_logistic",
        {
            "train_bars": 300,
            "feature_mode": "prices_macro",
            "macro_series_ids": ["DFF", "CPIAUCSL"],
            "macro_pca_enabled": True,
            "macro_features_mode": "changes_only",
            "macro_pca_input_mode": "changes_only",
            "macro_pca_variance_threshold": 0.9,
        },
    )
    assert params["macro_pca_enabled"] is True
    assert params["macro_pca_input_mode"] == "changes_only"
    assert params["macro_pca_variance_threshold"] == 0.9
