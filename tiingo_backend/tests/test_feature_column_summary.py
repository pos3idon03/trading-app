from features.ml.feature_column_summary import build_feature_groups, feature_group_labels
from features.ml.price_features import FEATURE_NAMES


def test_build_feature_groups_splits_price_and_volume():
    names = list(FEATURE_NAMES)
    groups = build_feature_groups(names, {"feature_mode": "prices_only"})
    assert "volume_rel_20" in groups["volume"]
    assert "ret_1" in groups["price"]
    assert "volume_rel_20" not in groups["price"]


def test_build_feature_groups_macro_and_strategy():
    names = [
        "ret_1",
        "volume_rel_20",
        "DFF_level",
        "DFF_chg_1m",
        "news_sent_avg_score_24h",
        "strat_rsi_reversion_signal",
        "ctx_1w_ret_5",
    ]
    groups = build_feature_groups(
        names,
        {
            "feature_mode": "prices_macro",
            "macro_series_ids": ["DFF"],
            "include_news_sentiment": True,
        },
        macro_series_ids=["DFF"],
    )
    assert groups["macro"] == ["DFF_level", "DFF_chg_1m"]
    assert groups["news"] == ["news_sent_avg_score_24h"]
    assert groups["strategy"] == ["strat_rsi_reversion_signal"]
    assert groups["context"] == ["ctx_1w_ret_5"]


def test_feature_group_labels_has_volume():
    labels = feature_group_labels()
    assert labels["volume"] == "Volume"
