"""Account-level HRP rebalancing across deployments."""

from __future__ import annotations

from typing import Any

from features.portfolio.hrp import weights_for_symbols


def compute_deployment_targets(
    *,
    symbols: list[str],
    returns_matrix: list[list[float]],
    linkage_method: str = "single",
    max_position_pct: float = 5.0,
) -> dict[str, float]:
    weights = weights_for_symbols(
        returns_matrix,
        symbols,
        linkage_method=linkage_method,
    )
    cap = max_position_pct / 100.0
    return {sym: min(w, cap) for sym, w in weights.items()}


def rebalance_plan(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    *,
    min_delta: float = 0.01,
) -> dict[str, float]:
    plan: dict[str, float] = {}
    for sym, target in target_weights.items():
        current = current_weights.get(sym, 0.0)
        delta = target - current
        if abs(delta) >= min_delta:
            plan[sym] = round(delta, 6)
    return plan
