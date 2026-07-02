from features.rl.reward import mean_variance_reward


def test_higher_lambda_penalizes_volatility():
    low = mean_variance_reward(0.01, 0.001, risk_aversion_lambda=0.0)
    high = mean_variance_reward(0.01, 0.001, risk_aversion_lambda=10.0)
    assert high < low
