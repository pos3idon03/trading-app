"""Load persisted DDQN artifacts and generate greedy signals."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import instrument_dal, rl_model_dal
from features.backtesting.bar_loader import load_backtest_bars
from features.rl.catalog import validate_rl_params
from features.rl.ddqn_agent import DdqnAgent, DdqnConfig
from features.rl.signals import greedy_signals_from_agent
from features.rl.state_builder import StateBuilder
from features.rl.trading_env import TradingEnv, TradingEnvConfig


def load_rl_artifact(path: str) -> dict[str, Any]:
    import torch

    return torch.load(path, map_location="cpu", weights_only=False)


async def run_rl_inference_for_symbol(
    session: AsyncSession,
    *,
    model_id: UUID,
    symbol: str,
    timeframe: str,
    start,
    end,
    params: dict | None = None,
) -> dict[str, Any]:
    saved = await rl_model_dal.get_model(session, model_id)
    if not saved or not saved.get("artifact_path"):
        raise LookupError(f"RL model not found: {model_id}")

    hyperparams = {**(saved.get("hyperparams") or {}), **(params or {})}
    validated = validate_rl_params(saved["model_type"], hyperparams)

    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    bars = await load_backtest_bars(
        session,
        instrument_id=instrument["id"],
        timeframe=timeframe,
        start=start,
        end=end,
    )

    payload = load_rl_artifact(saved["artifact_path"])
    builder: StateBuilder = payload["state_builder"]
    schema = saved.get("state_schema") or {}

    env_cfg = TradingEnvConfig(
        state_window=int(validated["state_window"]),
        risk_aversion_lambda=float(validated["risk_aversion_lambda"]),
        reward_mode=str(validated.get("reward_mode") or "sharpe_annual"),
        decision_timeframe=timeframe,
        commission_bps=float(validated["commission_bps"]),
        slippage_bps=float(validated["slippage_bps"]),
    )
    env = TradingEnv(bars, env_cfg, builder)
    state_dim = int(schema.get("state_dim", env.state_dim))
    n_actions = int(schema.get("n_actions", env.n_actions))

    agent = DdqnAgent(
        state_dim=state_dim,
        n_actions=n_actions,
        config=DdqnConfig(gamma=float(validated["gamma"])),
    )
    agent.online.load_state_dict(payload["online"])
    agent.target.load_state_dict(payload.get("target", payload["online"]))

    signals = greedy_signals_from_agent(agent, env, bars)
    return {
        "signals": signals,
        "symbol": symbol.upper(),
        "bars": bars,
        "hyperparams": validated,
        "model_id": str(model_id),
    }
