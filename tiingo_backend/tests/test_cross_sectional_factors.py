from features.ml.cross_sectional_factors import build_factor_features_at_index


def test_factor_features_shape():
    log_returns = {
        "A": [None, 0.01, 0.02, -0.01],
        "B": [None, 0.02, 0.01, 0.0],
    }
    result = build_factor_features_at_index(
        log_returns,
        ["A", "B"],
        3,
        lookback=2,
    )
    assert "A" in result
    assert len(result["A"]) == 3
