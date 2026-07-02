from features.rl.reward import sharpe_annual_step_reward


def test_sharpe_annual_reward_positive_on_gain():
    reward = sharpe_annual_step_reward(0.01, bars_per_year=252.0)
    assert reward > 0
