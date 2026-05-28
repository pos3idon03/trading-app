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


def test_validate_ml_params_defaults_inference_eval_scope():
    params = validate_ml_params("ml_logistic", {"feature_mode": "prices_only"})
    assert params["inference_eval_scope"] == "holdout"


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


def test_validate_ml_params_merges_defaults():
    params = validate_ml_params("ml_logistic", {"train_bars": 120})
    assert params["train_bars"] == 120
    assert params["feature_mode"] == "prices_only"


def test_validate_ml_params_accepts_train_bars_of_10():
    params = validate_ml_params("ml_logistic", {"train_bars": 10, "test_bars": 20})
    assert params["train_bars"] == 10
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
