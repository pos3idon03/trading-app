from typing import Any

DEFAULT_RL_PARAMS: dict[str, Any] = {
    "state_window": 32,
    "risk_aversion_lambda": 2.0,
    "risk_vol_span": 20,
    "action_position_pct": 100.0,
    "gamma": 0.99,
    "replay_capacity": 50_000,
    "batch_size": 64,
    "epsilon_decay_steps": 10_000,
    "target_sync_steps": 500,
    "train_episodes": 5,
    "commission_bps": 5.0,
    "slippage_bps": 0.0,
    "reward_clip": 0.05,
    "reward_mode": "sharpe_annual",
    "episode_sharpe_bonus_weight": 0.1,
}

RL_MODEL_CATALOG: dict[str, dict[str, Any]] = {
    "rl_ddqn": {
        "label": "Double DQN",
        "description": (
            "Double DQN with OHLCV+indicator state and Sharpe-annual reward. "
            "Actions: 0=hold, 1=buy, 2=sell (long-only)."
        ),
        "params": DEFAULT_RL_PARAMS,
        "constraints": {
            "state_window": (8, 128),
            "risk_aversion_lambda": (0.0, 20.0),
            "train_episodes": (1, 100),
        },
    },
}


def list_rl_models() -> list[dict[str, Any]]:
    return [{"id": k, **v} for k, v in RL_MODEL_CATALOG.items()]


def validate_rl_params(model_type: str, params: dict | None) -> dict:
    if model_type not in RL_MODEL_CATALOG:
        raise ValueError(f"Unknown RL model type: {model_type}")
    meta = RL_MODEL_CATALOG[model_type]
    merged = {**DEFAULT_RL_PARAMS, **(params or {})}
    for key, bounds in meta.get("constraints", {}).items():
        if key not in merged:
            continue
        value = float(merged[key])
        low, high = bounds
        if value < low or value > high:
            raise ValueError(f"Parameter {key} must be between {low} and {high}")
    return merged
