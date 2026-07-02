"""Reward shaping for RL trading."""

from __future__ import annotations

import math


def ewma_variance(returns: list[float], span: int = 20) -> float:
    if not returns:
        return 0.0
    alpha = 2.0 / (span + 1.0)
    var = returns[0] ** 2
    for r in returns[1:]:
        var = alpha * (r ** 2) + (1.0 - alpha) * var
    return var


def mean_variance_reward(
    log_return: float,
    trailing_var: float,
    *,
    risk_aversion_lambda: float,
    turnover_cost: float = 0.0,
    drawdown_penalty: float = 0.0,
    reward_clip: float = 0.05,
) -> float:
    reward = log_return - (risk_aversion_lambda / 2.0) * trailing_var
    reward -= turnover_cost
    reward -= drawdown_penalty
    return max(-reward_clip, min(reward_clip, reward))


def sharpe_annual_step_reward(
    log_return: float,
    *,
    bars_per_year: float,
    commission_drag: float = 0.0,
    reward_clip: float = 0.05,
) -> float:
    annualized = log_return * bars_per_year
    reward = annualized - commission_drag
    return max(-reward_clip, min(reward_clip, reward))


def episode_sharpe_bonus(returns: list[float], weight: float = 0.1) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / len(returns)
    std = math.sqrt(var) if var > 0 else 0.0
    if std <= 1e-9:
        return 0.0
    return weight * (mean / std)
