"""Account-level HRP rebalance hook for live execution."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from dal import trading_deployment_dal
from features.execution.portfolio_rebalancer import compute_deployment_targets, rebalance_plan
from features.execution.portfolio_snapshot import build_portfolio_breakdown


async def maybe_rebalance_active_deployments(session: AsyncSession) -> dict:
    deployments = await trading_deployment_dal.list_active_deployments(session)
    hrp_deployments = [
        d for d in deployments
        if str((d.get("hyperparams_snapshot") or {}).get("sizing_method") or "") == "hrp"
    ]
    if len(hrp_deployments) < 2:
        return {"skipped": True, "reason": "insufficient HRP deployments"}

    breakdown = await build_portfolio_breakdown(session)
    current_weights = {
        row["symbol"]: float(row.get("weight_pct") or 0.0) / 100.0
        for row in breakdown.get("positions") or []
    }
    symbols = sorted(current_weights.keys())
    if len(symbols) < 2:
        return {"skipped": True, "reason": "insufficient open positions"}

    hyper = hrp_deployments[0].get("hyperparams_snapshot") or {}
    returns_matrix = hyper.get("hrp_returns_matrix") or []
    if not returns_matrix:
        return {"skipped": True, "reason": "missing returns matrix in deployment config"}

    targets = compute_deployment_targets(
        symbols=symbols,
        returns_matrix=returns_matrix,
        linkage_method=str(hyper.get("hrp_linkage_method") or "single"),
        max_position_pct=float(hyper.get("max_position_pct") or 5.0),
    )
    plan = rebalance_plan(current_weights, targets)
    return {"skipped": False, "plan": plan, "targets": targets}
