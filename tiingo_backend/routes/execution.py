from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from dtos.execution_dto import (
    AccountSnapshotDTO,
    CreateDeploymentRequest,
    EvaluateAllResponse,
    EvaluateDeploymentResponse,
    ExecutionActivityEventDTO,
    ExecutionEvaluationsResponse,
    ExecutionOrderDTO,
    ExecutionOrdersResponse,
    ExecutionStatusDTO,
    KillSwitchRequest,
    KillSwitchResponse,
    PortfolioResponse,
    PositionSnapshotDTO,
    RiskConfigDTO,
    TradingDeploymentDTO,
    TradingDeploymentsResponse,
)
from features.execution.activity_format import evaluation_row_to_activity
from features.execution.orchestrator import (
    activate_deployment,
    create_deployment,
    evaluate_all_active,
    evaluate_deployment,
    get_deployment,
    get_execution_status,
    get_portfolio_snapshot,
    get_risk_config,
    list_deployments,
    list_evaluations,
    list_orders,
    pause_deployment,
    set_kill_switch,
    stop_deployment,
)
from features.execution.ws_handler import stream_execution_activity
from features.worker.tasks import create_and_enqueue_job

router = APIRouter(prefix="/execution", tags=["execution"])


def _deployment_dto(row: dict) -> TradingDeploymentDTO:
    return TradingDeploymentDTO(
        id=row["id"],
        model_id=row["model_id"],
        symbol=row["symbol"],
        timeframe=row["timeframe"],
        status=row["status"],
        trading_mode=row["trading_mode"],
        allocation_pct=row["allocation_pct"],
        hyperparams_snapshot=row.get("hyperparams_snapshot") or {},
        model_name=row.get("model_name"),
        model_type=row.get("model_type"),
        feature_mode=row.get("feature_mode"),
        last_evaluated_bar_time=row.get("last_evaluated_bar_time"),
        last_signal=row.get("last_signal"),
        last_error=row.get("last_error"),
        last_blocked_reason=row.get("last_blocked_reason"),
        last_probability=row.get("last_probability"),
        last_outcome=row.get("last_outcome"),
        activated_at=row.get("activated_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _order_dto(row: dict) -> ExecutionOrderDTO:
    return ExecutionOrderDTO(
        id=row["id"],
        deployment_id=row["deployment_id"],
        alpaca_order_id=row.get("alpaca_order_id"),
        symbol=row["symbol"],
        side=row["side"],
        qty=row["qty"],
        order_type=row["order_type"],
        status=row["status"],
        signal=row["signal"],
        bar_time=row["bar_time"],
        filled_avg_price=row.get("filled_avg_price"),
        submitted_at=row["submitted_at"],
        filled_at=row.get("filled_at"),
        error_message=row.get("error_message"),
        model_name=row.get("model_name"),
        model_id=row.get("model_id"),
    )


def _activity_dto(row: dict) -> ExecutionActivityEventDTO:
    return ExecutionActivityEventDTO(**evaluation_row_to_activity(row))


@router.websocket("/ws")
async def execution_activity_ws(websocket: WebSocket) -> None:
    await stream_execution_activity(websocket)


@router.get("/status", response_model=ExecutionStatusDTO)
async def execution_status(session: AsyncSession = Depends(get_db)) -> ExecutionStatusDTO:
    row = await get_execution_status(session)
    return ExecutionStatusDTO(**row)


@router.post("/kill-switch", response_model=KillSwitchResponse)
async def kill_switch(
    body: KillSwitchRequest,
    session: AsyncSession = Depends(get_db),
) -> KillSwitchResponse:
    row = await set_kill_switch(session, body.enabled)
    return KillSwitchResponse(
        kill_switch_enabled=row["kill_switch_enabled"],
        updated_at=row["updated_at"],
    )


@router.get("/risk-config", response_model=RiskConfigDTO)
async def risk_config() -> RiskConfigDTO:
    return RiskConfigDTO(**await get_risk_config())


@router.get("/portfolio", response_model=PortfolioResponse)
async def portfolio() -> PortfolioResponse:
    try:
        snapshot = await get_portfolio_snapshot()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return PortfolioResponse(
        account=AccountSnapshotDTO(**snapshot["account"]),
        positions=[PositionSnapshotDTO(**row) for row in snapshot["positions"]],
    )


@router.get("/evaluations", response_model=ExecutionEvaluationsResponse)
async def get_evaluations(
    deployment_id: UUID | None = Query(default=None),
    symbol: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> ExecutionEvaluationsResponse:
    rows = await list_evaluations(
        session,
        deployment_id=deployment_id,
        symbol=symbol,
        limit=limit,
    )
    return ExecutionEvaluationsResponse(
        evaluations=[_activity_dto(row) for row in rows],
    )


@router.get("/deployments", response_model=TradingDeploymentsResponse)
async def get_deployments(
    session: AsyncSession = Depends(get_db),
) -> TradingDeploymentsResponse:
    rows = await list_deployments(session)
    return TradingDeploymentsResponse(deployments=[_deployment_dto(row) for row in rows])


@router.post("/deployments", response_model=TradingDeploymentDTO, status_code=status.HTTP_201_CREATED)
async def post_deployment(
    body: CreateDeploymentRequest,
    session: AsyncSession = Depends(get_db),
) -> TradingDeploymentDTO:
    try:
        row = await create_deployment(
            session,
            model_id=body.model_id,
            allocation_pct=body.allocation_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _deployment_dto(row)


@router.get("/deployments/{deployment_id}", response_model=TradingDeploymentDTO)
async def get_deployment_route(
    deployment_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> TradingDeploymentDTO:
    row = await get_deployment(session, deployment_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deployment_id}")
    return _deployment_dto(row)


@router.post("/deployments/{deployment_id}/activate", response_model=TradingDeploymentDTO)
async def activate_deployment_route(
    deployment_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> TradingDeploymentDTO:
    try:
        row = await activate_deployment(session, deployment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _deployment_dto(row)


@router.post("/deployments/{deployment_id}/pause", response_model=TradingDeploymentDTO)
async def pause_deployment_route(
    deployment_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> TradingDeploymentDTO:
    try:
        row = await pause_deployment(session, deployment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _deployment_dto(row)


@router.post("/deployments/{deployment_id}/stop", response_model=TradingDeploymentDTO)
async def stop_deployment_route(
    deployment_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> TradingDeploymentDTO:
    try:
        row = await stop_deployment(session, deployment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _deployment_dto(row)


@router.post("/deployments/{deployment_id}/evaluate", response_model=EvaluateDeploymentResponse)
async def evaluate_deployment_route(
    deployment_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> EvaluateDeploymentResponse:
    try:
        result = await evaluate_deployment(session, deployment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return EvaluateDeploymentResponse(
        deployment_id=deployment_id,
        skipped=result.get("skipped", False),
        signal=result.get("signal"),
        bar_time=result.get("bar_time"),
        probability=result.get("probability"),
        warnings=result.get("warnings") or [],
        order=result.get("order"),
        blocked_reason=result.get("blocked_reason"),
        outcome=result.get("outcome"),
        error=result.get("error"),
    )


@router.post("/evaluate-all", response_model=EvaluateAllResponse)
async def evaluate_all_route(
    session: AsyncSession = Depends(get_db),
) -> EvaluateAllResponse:
    try:
        result = await evaluate_all_active(session)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return EvaluateAllResponse(**result)


@router.post("/evaluate-all/enqueue", status_code=status.HTTP_202_ACCEPTED)
async def enqueue_evaluate_all(
    session: AsyncSession = Depends(get_db),
) -> dict:
    job = await create_and_enqueue_job(session, "execution_evaluate_all", {})
    return {"job_id": str(job["id"]), "status": job["status"]}


@router.get("/orders", response_model=ExecutionOrdersResponse)
async def get_orders(
    deployment_id: UUID | None = Query(default=None),
    symbol: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_db),
) -> ExecutionOrdersResponse:
    rows = await list_orders(
        session,
        deployment_id=deployment_id,
        symbol=symbol,
        status=status_filter,
    )
    return ExecutionOrdersResponse(orders=[_order_dto(row) for row in rows])
