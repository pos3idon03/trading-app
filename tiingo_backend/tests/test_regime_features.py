import pytest

from features.ml.regime_features import (
    INDICATOR_GROUPS,
    classify_regime,
    resolve_enabled_indicator_groups,
    select_features_for_regime,
)


def test_classify_regime_buckets():
    assert classify_regime(0.01, 0.02, 0.05) == "low_vol"
    assert classify_regime(0.06, 0.02, 0.05) == "high_vol"


def test_select_features_prefers_vol_in_high_regime():
    names = ["ret_5", "rsi_14", "vol_20", "atr_14"]
    importances = {n: 1.0 for n in names}
    selected = select_features_for_regime(names, importances, "high_vol", top_n=2)
    assert all(s in names for s in selected)


def test_select_features_respects_enabled_groups_only():
    names = ["ret_5", "ret_20", "rsi_14", "vol_20"]
    importances = {n: 1.0 for n in names}
    enabled = frozenset({"momentum"})
    selected = select_features_for_regime(
        names,
        importances,
        "low_vol",
        top_n=5,
        enabled_groups=enabled,
    )
    assert all(s in INDICATOR_GROUPS["momentum"] for s in selected)
    assert "rsi_14" not in selected


def test_resolve_enabled_indicator_groups_defaults():
    groups = resolve_enabled_indicator_groups({})
    assert groups == frozenset({"momentum", "mean_reversion", "volatility"})


def test_resolve_enabled_indicator_groups_subset():
    groups = resolve_enabled_indicator_groups(
        {"indicator_groups": ["momentum", "volatility"]},
    )
    assert groups == frozenset({"momentum", "volatility"})


def test_resolve_enabled_indicator_groups_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown indicator_groups"):
        resolve_enabled_indicator_groups({"indicator_groups": ["momentum", "invalid"]})


def test_validate_indicator_groups_via_catalog():
    from features.ml.catalog import validate_ml_params

    params = validate_ml_params(
        "ml_logistic",
        {
            "dynamic_indicator_selection": True,
            "indicator_groups": ["momentum"],
        },
    )
    assert params["indicator_groups"] == ["momentum"]
