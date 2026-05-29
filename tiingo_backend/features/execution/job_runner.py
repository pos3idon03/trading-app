from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from features.execution.deployment_reconciliation import reconcile_missed_updates
from features.execution.evaluation_cycle import (
    refresh_active_deployment_market_data,
    run_deployment_cycle,
)
from features.execution.orchestrator import evaluate_all_active, evaluate_deployment
from features.ingestion.deployment_ohlcv_refresh import refresh_single_deployment_ohlcv


def parse_scheduled_at(params: dict) -> datetime | None:
    raw = params.get("scheduled_at")
    if not raw:
        return None
    parsed = datetime.fromisoformat(str(raw))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


async def execute_execution_job(
    session: AsyncSession,
    job_type: str,
    params: dict,
    job_id: UUID | None = None,
) -> dict:
    if job_type == "execution_deployment_cycle":
        return await run_deployment_cycle(session, as_of=parse_scheduled_at(params))
    if job_type == "execution_deployment_reconciliation":
        return await reconcile_missed_updates(session)
    if job_type == "execution_evaluate_all":
        return await evaluate_all_active(session)
    if job_type == "execution_evaluate_one":
        deployment_id = params.get("deployment_id")
        if not deployment_id:
            raise ValueError("deployment_id is required for execution_evaluate_one")
        return await evaluate_deployment(session, UUID(str(deployment_id)))
    raise ValueError(f"Unknown execution job type: {job_type}")


async def execute_deployment_data_job(
    session: AsyncSession,
    job_type: str,
    params: dict,
) -> dict:
    if job_type == "deployment_market_data_refresh":
        timeframes = params.get("timeframes")
        tf_set = set(timeframes) if timeframes else None
        return await refresh_active_deployment_market_data(session, timeframes=tf_set)
    raise ValueError(f"Unknown deployment data job type: {job_type}")


async def refresh_deployment_market_data(
    session: AsyncSession,
    deployment: dict,
) -> dict:
    results = await refresh_single_deployment_ohlcv(session, deployment)
    await session.commit()
    return {"results": results}
