from features.portfolio.hrp import compute_hrp_weights, weights_for_symbols


def test_hrp_weights_sum_to_one():
    returns = [[0.01, 0.02], [0.02, 0.01], [-0.01, 0.0], [0.0, -0.01]] * 10
    weights = compute_hrp_weights(returns)
    assert len(weights) == 2
    assert abs(sum(weights.values()) - 1.0) < 1e-6


def test_weights_for_symbols_keys():
    returns = [[0.01, -0.01], [0.02, 0.0], [-0.01, 0.01]] * 15
    w = weights_for_symbols(returns, ["A", "B"])
    assert set(w.keys()) == {"A", "B"}
    assert abs(sum(w.values()) - 1.0) < 1e-6
