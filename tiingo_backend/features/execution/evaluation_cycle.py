from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import trading_deployment_dal
from features.execution.alpaca_symbols import execution_asset_type
from features.execution.deployment_timeframes import should_evaluate_timeframe
from features.execution.orchestrator import evaluate_deployment
from features.ingestion.deployment_ohlcv_refresh import (
    build_deployment_fetch_plan,
    refresh_deployment_ohlcv,
)
from utils.logging import get_logger

logger = get_logger(__name__)


def group_due_deployments_by_timeframe(
    deployments: list[dict],
    as_of: datetime,
    *,
    force_timeframes: set[str] | None = None,
) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = {}
    for deployment in deployments:
        timeframe = deployment["timeframe"]
        if force_timeframes is not None and timeframe not in force_timeframes:
            continue
        asset_type = execution_asset_type(deployment.get("asset_type"))
        if not should_evaluate_timeframe(timeframe, as_of, asset_type=asset_type):
            continue
        buckets.setdefault(timeframe, []).append(deployment)
    return buckets


async def run_deployment_cycle(
    session: AsyncSession,
    *,
    as_of: datetime | None = None,
    force_timeframes: set[str] | None = None,
    skip_reconciliation: bool = False,
) -> dict:
    now = as_of or datetime.now(timezone.utc)
    active = await trading_deployment_dal.list_active_deployments_with_instrument(session)
    if not active:
        return {"skipped": True, "reason": "no active deployments", "results": []}

    due_buckets = group_due_deployments_by_timeframe(
        active,
        now,
        force_timeframes=force_timeframes,
    )
    if not due_buckets:
        result = {"skipped": True, "reason": "no deployments due", "results": []}
        if not skip_reconciliation:
            result["reconciliation"] = await _run_reconciliation(session)
        return result

    cycle_results: list[dict] = []
    for timeframe in sorted(due_buckets):
        deployments = due_buckets[timeframe]
        if not deployments:
            continue

        plan = await build_deployment_fetch_plan(session, deployment_timeframes={timeframe})
        refresh_results = await refresh_deployment_ohlcv(session, plan)

        eval_results: list[dict] = []
        for deployment in deployments:
            try:
                outcome = await evaluate_deployment(session, deployment["id"])
                eval_results.append(outcome)
            except Exception as exc:
                await trading_deployment_dal.update_deployment_status(
                    session,
                    deployment["id"],
                    status="error",
                    last_error=str(exc),
                )
                await session.commit()
                eval_results.append(
                    {
                        "deployment_id": str(deployment["id"]),
                        "error": str(exc),
                    },
                )

        cycle_results.append(
            {
                "timeframe": timeframe,
                "refresh": refresh_results,
                "evaluations": eval_results,
            },
        )
        logger.info(
            "deployment_cycle_completed",
            timeframe=timeframe,
            deployments=len(deployments),
            refreshed=len(refresh_results),
        )

    result = {
        "skipped": False,
        "as_of": now.isoformat(),
        "timeframes": sorted(due_buckets),
        "results": cycle_results,
    }
    if not skip_reconciliation:
        result["reconciliation"] = await _run_reconciliation(session)
    return result


async def _run_reconciliation(session: AsyncSession) -> dict:
    from features.execution.deployment_reconciliation import reconcile_missed_updates

    return await reconcile_missed_updates(session)


async def refresh_active_deployment_market_data(
    session: AsyncSession,
    *,
    timeframes: set[str] | None = None,
) -> dict:
    plan = await build_deployment_fetch_plan(session, deployment_timeframes=timeframes)
    if plan.is_empty:
        return {"skipped": True, "reason": "no active deployments or targets", "results": []}

    results = await refresh_deployment_ohlcv(session, plan)
    await session.commit()
    return {"skipped": False, "results": results}


async def evaluate_deployments_for_timeframe(
    session: AsyncSession,
    timeframe: str,
    deployment_ids: list[UUID] | None = None,
) -> list[dict]:
    active = await trading_deployment_dal.list_active_deployments(session)
    targets = [row for row in active if row["timeframe"] == timeframe]
    if deployment_ids is not None:
        allowed = {str(item) for item in deployment_ids}
        targets = [row for row in targets if str(row["id"]) in allowed]

    outcomes: list[dict] = []
    for deployment in targets:
        try:
            outcomes.append(await evaluate_deployment(session, deployment["id"]))
        except Exception as exc:
            await trading_deployment_dal.update_deployment_status(
                session,
                deployment["id"],
                status="error",
                last_error=str(exc),
            )
            await session.commit()
            outcomes.append({"deployment_id": str(deployment["id"]), "error": str(exc)})
    return outcomes
