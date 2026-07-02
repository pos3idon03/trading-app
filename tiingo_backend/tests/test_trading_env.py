from datetime import datetime, timezone

from features.rl.state_builder import StateBuilder
from features.rl.trading_env import TradingEnv, TradingEnvConfig


def _bars(n: int = 60) -> list[dict]:
    bars = []
    price = 100.0
    for i in range(n):
        price *= 1.001
        bars.append({
            "time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open": price,
            "high": price,
            "low": price,
            "close": price,
        })
    return bars


def test_trading_env_valid_actions():
    env = TradingEnv(_bars(), TradingEnvConfig(state_window=10))
    env.reset()
    assert env.valid_actions() == [0, 1]
    env.shares = 10
    assert env.valid_actions() == [0, 2]


def test_state_builder_transform():
    builder = StateBuilder(state_window=5)
    builder.fit([[0.0] * 11, [1.0] * 11])
    out = builder.transform([0.0] * 11)
    assert len(out) == 11
