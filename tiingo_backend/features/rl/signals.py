"""Map DDQN actions to backtest signals."""

from features.rl.trading_env import TradingEnv


def action_to_signal(action: int) -> str:
    if action == TradingEnv.ACTION_ENTER:
        return "buy"
    if action == TradingEnv.ACTION_EXIT:
        return "sell"
    return "hold"


def greedy_signals_from_agent(agent, env: TradingEnv, bars: list[dict]) -> list[str]:
    signals = ["hold"] * len(bars)
    state = env.reset()
    done = False
    while not done:
        idx = env.index
        valid = env.valid_actions()
        action = agent.select_action(state, valid, explore=False)
        signals[idx] = action_to_signal(action)
        state, _, done, _ = env.step(action)
        agent.tick()
    return signals
