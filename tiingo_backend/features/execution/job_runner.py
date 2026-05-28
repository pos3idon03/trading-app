from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from features.execution.orchestrator import evaluate_all_active, evaluate_deployment


async def execute_execution_job(
    session: AsyncSession,
    job_type: str,
    params: dict,
    job_id: UUID | None = None,
) -> dict:
    if job_type == "execution_evaluate_all":
        return await evaluate_all_active(session)
    if job_type == "execution_evaluate_one":
        deployment_id = params.get("deployment_id")
        if not deployment_id:
            raise ValueError("deployment_id is required for execution_evaluate_one")
        return await evaluate_deployment(session, UUID(str(deployment_id)))
    raise ValueError(f"Unknown execution job type: {job_type}")
