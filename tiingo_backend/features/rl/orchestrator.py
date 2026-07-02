"""Train and evaluate DDQN agents."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from dal import instrument_dal
from features.backtesting.bar_loader import load_backtest_bars
from features.backtesting.engine import run_backtest_with_signals
from features.backtesting.metrics import compute_backtest_metrics
from features.rl.catalog import validate_rl_params
from features.rl.ddqn_agent import DdqnAgent, DdqnConfig
from features.rl.signals import greedy_signals_from_agent
from features.rl.state_builder import StateBuilder
from features.rl.trading_env import TradingEnv, TradingEnvConfig


async def train_rl_agent_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    model_type: str,
    params: dict | None,
    timeframe: str,
    start,
    end,
) -> dict[str, Any]:
    validated = validate_rl_params(model_type, params)
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
    if len(bars) < validated["state_window"] + 10:
        raise ValueError("Insufficient bars for RL training")

    env_cfg = TradingEnvConfig(
        state_window=int(validated["state_window"]),
        risk_aversion_lambda=float(validated["risk_aversion_lambda"]),
        risk_vol_span=int(validated["risk_vol_span"]),
        commission_bps=float(validated["commission_bps"]),
        slippage_bps=float(validated["slippage_bps"]),
        action_position_pct=float(validated["action_position_pct"]),
        reward_clip=float(validated["reward_clip"]),
        reward_mode=str(validated.get("reward_mode") or "sharpe_annual"),
        decision_timeframe=timeframe,
        episode_sharpe_bonus_weight=float(
            validated.get("episode_sharpe_bonus_weight") or 0.1
        ),
    )
    builder = StateBuilder(state_window=env_cfg.state_window)
    train_vectors = [
        builder.build_state(
            bars,
            i,
            position_flag=0.0,
            position_age=0.0,
            unrealized_pnl_pct=0.0,
            cash_weight=1.0,
            drawdown_pct=0.0,
            realized_vol=0.0,
        )
        for i in range(env_cfg.state_window, len(bars) - 1)
    ]
    builder.fit(train_vectors)

    env = TradingEnv(bars, env_cfg, builder)
    agent = DdqnAgent(
        state_dim=env.state_dim,
        n_actions=env.n_actions,
        config=DdqnConfig(
            gamma=float(validated["gamma"]),
            batch_size=int(validated["batch_size"]),
            replay_capacity=int(validated["replay_capacity"]),
            target_sync_steps=int(validated["target_sync_steps"]),
            epsilon_decay_steps=int(validated["epsilon_decay_steps"]),
        ),
    )

    episodes = int(validated["train_episodes"])
    total_reward = 0.0
    for _ in range(episodes):
        state = env.reset()
        done = False
        while not done:
            valid = env.valid_actions()
            action = agent.select_action(state, valid, explore=True)
            next_state, reward, done, _ = env.step(action)
            agent.remember(state, action, reward, next_state, done, env.valid_actions())
            agent.train_step()
            agent.tick()
            state = next_state
            total_reward += reward

    signals = greedy_signals_from_agent(agent, TradingEnv(bars, env_cfg, builder), bars)
    sim = run_backtest_with_signals(
        bars,
        signals,
        initial_cash=10_000.0,
        commission_bps=float(validated["commission_bps"]),
        decision_timeframe=timeframe,
        slippage_bps=float(validated["slippage_bps"]),
    )
    metrics = compute_backtest_metrics(sim, bars, decision_timeframe=timeframe)

    return {
        "agent": agent,
        "state_builder": builder,
        "signals": signals,
        "simulation": sim,
        "metrics": metrics,
        "train_reward": total_reward,
        "hyperparams": validated,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
    }


async def persist_rl_model(
    session: AsyncSession,
    *,
    name: str,
    train_result: dict[str, Any],
) -> UUID:
    from pathlib import Path

    import torch

    from config import settings
    from dal import rl_model_dal

    model_id = uuid4()
    artifact_dir = Path(settings.ml_artifact_dir) / "rl"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"{model_id}.pt"
    agent: DdqnAgent = train_result["agent"]
    torch.save(
        {
            "online": agent.online.state_dict(),
            "target": agent.target.state_dict(),
            "state_builder": train_result["state_builder"],
        },
        path,
    )
    await rl_model_dal.create_model(
        session,
        model_id=model_id,
        name=name,
        model_type="rl_ddqn",
        symbol=train_result["symbol"],
        timeframe=train_result["timeframe"],
        hyperparams=train_result["hyperparams"],
        state_schema={"state_dim": agent.state_dim, "n_actions": agent.n_actions},
        train_metrics={
            "total_reward": train_result["train_reward"],
            "metrics": train_result["metrics"],
        },
        artifact_path=str(path),
    )
    return model_id
