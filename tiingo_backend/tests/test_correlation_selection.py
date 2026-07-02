from features.ml.correlation_selection import prune_correlated_features


def test_prune_removes_collinear_feature():
    x_train = [
        [1.0, 2.0, 5.0],
        [2.0, 4.0, 1.0],
        [3.0, 6.0, 3.0],
        [4.0, 8.0, 2.0],
    ]
    names = ["a", "b", "c"]
    mask, pruned = prune_correlated_features(x_train, names, threshold=0.75)
    assert "b" in pruned
    assert len(mask) == 2
