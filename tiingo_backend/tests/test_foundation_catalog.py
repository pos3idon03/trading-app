import pytest

from features.foundation.catalog import (
    validate_foundation_params,
    minimum_bars_required,
    FOUNDATION_MODEL_CATALOG,
)


def test_catalog_has_timesfm_and_chronos():
    assert "foundation_timesfm_2_5" in FOUNDATION_MODEL_CATALOG
    assert "foundation_chronos_2" in FOUNDATION_MODEL_CATALOG


def test_validate_foundation_params_merges_defaults():
    params = validate_foundation_params("foundation_timesfm_2_5", {"context_length": 64})
    assert params["context_length"] == 64
    assert params["forecast_horizon"] == 5
    assert params["signal_mode"] == "next_point"


def test_validate_rejects_unknown_model():
    with pytest.raises(ValueError, match="Unknown foundation model_type"):
        validate_foundation_params("foundation_unknown", {})


def test_validate_rejects_inverted_thresholds():
    with pytest.raises(ValueError, match="buy_return_threshold"):
        validate_foundation_params(
            "foundation_timesfm_2_5",
            {"buy_return_threshold": -0.01, "sell_return_threshold": 0.01},
        )


def test_minimum_bars_required():
    params = validate_foundation_params("foundation_chronos_2", {})
    assert minimum_bars_required(params) == params["context_length"] + params["forecast_horizon"] + 1
