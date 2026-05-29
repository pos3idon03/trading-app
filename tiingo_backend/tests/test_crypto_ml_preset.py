from features.ml.catalog import (
    CRYPTO_ML_PRESET,
    default_walk_forward_params,
    get_crypto_ml_preset,
    validate_ml_params,
)


def test_crypto_preset_uses_meta_label_and_macro():
    preset = get_crypto_ml_preset("1h")
    assert preset["label_mode"] == "meta_label"
    assert preset["feature_mode"] == "prices_macro"
    assert "T10Y2Y" in preset["macro_series_ids"]
    assert preset["include_news_sentiment"] is True
    assert preset["slippage_bps"] == 5.0


def test_validate_meta_label_params():
    params = validate_ml_params(
        "ml_xgboost",
        {**CRYPTO_ML_PRESET, **default_walk_forward_params("1h", asset_type="crypto")},
        "1h",
        asset_type="crypto",
    )
    assert params["label_mode"] == "meta_label"
    assert params["meta_gate_threshold"] == 0.65


def test_crypto_hourly_walk_forward_defaults():
    wfo = default_walk_forward_params("1h", asset_type="crypto")
    assert wfo["train_bars"] > 1000
    assert wfo["test_bars"] >= 1
