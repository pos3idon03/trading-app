from features.ml.price_features import FEATURE_WARMUP_BARS, build_price_feature_matrix
from features.ml.walk_forward_diagnostics import (
    build_walk_forward_readiness,
    count_structural_walk_forward_folds,
    count_viable_walk_forward_folds,
)


def _bars(count: int, *, trend: float = 0.001) -> list[dict]:
    closes = [100.0]
    for _ in range(count - 1):
        closes.append(closes[-1] * (1 + trend))
    return [{"close": c, "high": c * 1.01, "low": c * 0.99} for c in closes]


def _choppy_bars(count: int) -> list[dict]:
    import random

    random.seed(7)
    closes = [100.0]
    for _ in range(count - 1):
        closes.append(closes[-1] * (1 + random.gauss(0, 0.012)))
    return [{"close": c, "high": c * 1.01, "low": c * 0.99} for c in closes]


def test_count_structural_walk_forward_folds():
    assert count_structural_walk_forward_folds(200, 60, 40, 40) == 3
    assert count_structural_walk_forward_folds(80, 60, 40, 40) == 0


def test_count_viable_folds_zero_when_all_features_null():
    labels = [0, 1] * 100
    feature_rows = [None] * 200
    assert count_viable_walk_forward_folds(feature_rows, labels, 60, 40, 40) == 0


def test_count_viable_folds_positive_on_choppy_data():
    bars = _choppy_bars(400)
    _, feature_rows = build_price_feature_matrix(bars)
    from features.ml.labels import build_labels

    labels = build_labels(bars, 5, label_mode="binary")
    viable = count_viable_walk_forward_folds(feature_rows, labels, 120, 60, 60)
    structural = count_structural_walk_forward_folds(len(bars), 120, 60, 60)
    assert structural > 0
    assert viable > 0


def test_build_readiness_flags_zero_features():
    bars = _bars(120)
    readiness = build_walk_forward_readiness(
        bars,
        [None] * len(bars),
        {
            "train_bars": 60,
            "test_bars": 30,
            "step_bars": 30,
            "label_horizon": 5,
            "label_mode": "binary",
            "label_threshold": 0.01,
            "label_method": "endpoint",
        },
    )
    assert readiness["valid_feature_rows"] == 0
    assert readiness["viable_folds"] == 0
    assert any("No valid feature rows" in issue for issue in readiness["readiness_issues"])


def test_build_readiness_warns_when_train_below_warmup():
    bars = _choppy_bars(300)
    _, feature_rows = build_price_feature_matrix(bars)
    readiness = build_walk_forward_readiness(
        bars,
        feature_rows,
        {
            "warmup_bars": FEATURE_WARMUP_BARS,
            "train_bars": FEATURE_WARMUP_BARS,
            "test_bars": 60,
            "step_bars": 60,
            "label_horizon": 5,
            "label_mode": "binary",
            "label_threshold": 0.01,
            "label_method": "endpoint",
        },
    )
    assert any("warmup" in issue.lower() for issue in readiness["readiness_issues"])


def test_monotonic_trend_may_have_zero_viable_folds():
    bars = _bars(400, trend=0.003)
    _, feature_rows = build_price_feature_matrix(bars)
    from features.ml.labels import build_labels

    labels = build_labels(bars, 2, label_mode="binary")
    viable = count_viable_walk_forward_folds(feature_rows, labels, 120, 60, 60)
    assert viable == 0
