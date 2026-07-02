from datetime import datetime

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from dtos.execution_dto import (
    AccountSnapshotDTO,
    CreateDeploymentRequest,
    DeleteDeploymentRequest,
    DeleteDeploymentResponse,
    DeploymentCycleEnqueueRequest,
    DeploymentOverviewDTO,
    DeploymentOverviewResponse,
    DeploymentRefreshResponse,
    EnqueueJobResponse,
    EvaluateAllResponse,
    EvaluateDeploymentResponse,
    ExecutionActivityEventDTO,
    ExecutionEvaluationsResponse,
    ExecutionOrderDTO,
    ExecutionOrdersResponse,
    ExecutionStatusDTO,
    DeploymentPositionSnapshotDTO,
    KillSwitchRequest,
    KillSwitchResponse,
    PortfolioPeriodDTO,
    PortfolioPositionRowDTO,
    PortfolioResponse,
    PortfolioSummaryDTO,
    PositionSnapshotDTO,
    ReconciliationResponse,
    RiskConfigDTO,
    TradingDeploymentDTO,
    TradingDeploymentsResponse,
    UntrackedPositionSnapshotDTO,
)
from dtos.execution_explainability_dto import ProbabilityExplainabilityDTO
from features.execution.activity_format import evaluation_row_to_activity
from features.execution.deployment_reconciliation import reconcile_missed_updates
from features.execution.job_runner import refresh_deployment_market_data
from features.execution.orchestrator import (
    activate_deployment,
    create_deployment,
    delete_deployment,
    evaluate_all_active,
    evaluate_deployment,
    get_deployment,
    get_deployment_overview,
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


def _explainability_dto(data: dict | None) -> ProbabilityExplainabilityDTO | None:
    if not data:
        return None
    return ProbabilityExplainabilityDTO.model_validate(data)


def _overview_dto(row: dict) -> DeploymentOverviewDTO:
    return DeploymentOverviewDTO(
        id=row["id"],
        model_id=row["model_id"],
        symbol=row["symbol"],
        timeframe=row["timeframe"],
        status=row["status"],
        model_name=row.get("model_name"),
        last_error=row.get("last_error"),
        last_blocked_reason=row.get("last_blocked_reason"),
        last_signal=row.get("last_signal"),
        last_probability=row.get("last_probability"),
        buy_threshold=row.get("buy_threshold"),
        sell_threshold=row.get("sell_threshold"),
        last_explainability=_explainability_dto(row.get("last_explainability")),
        last_evaluated_bar_time=row.get("last_evaluated_bar_time"),
        last_evaluated_at=row.get("last_evaluated_at"),
        current_price=row.get("current_price"),
        price_updated_at=row.get("price_updated_at"),
        round_trip_count=int(row.get("round_trip_count") or 0),
        open_position_count=int(row.get("open_position_count") or 0),
        order_count=int(row.get("order_count") or 0),
        open_order_count=int(row.get("open_order_count") or 0),
        strategy_profit=float(row.get("strategy_profit") or 0),
        strategy_profit_pct=row.get("strategy_profit_pct"),
        position_qty=float(row.get("position_qty") or 0),
        position_side=row.get("position_side") or "flat",
        update_status=row.get("update_status") or "unknown",
        expected_latest_bar_time=row.get("expected_latest_bar_time"),
        ohlcv_latest_bar_time=row.get("ohlcv_latest_bar_time"),
        missed_slot_count=int(row.get("missed_slot_count") or 0),
    )


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
        last_evaluated_at=row.get("last_evaluated_at"),
        last_signal=row.get("last_signal"),
        last_error=row.get("last_error"),
        last_blocked_reason=row.get("last_blocked_reason"),
        last_probability=row.get("last_probability"),
        last_outcome=row.get("last_outcome"),
        position_qty=float(row.get("position_qty") or 0),
        position_side=row.get("position_side") or "flat",
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
async def portfolio(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> PortfolioResponse:
    try:
        snapshot = await get_portfolio_snapshot(session, start=start, end=end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    summary = snapshot.get("summary")
    period = snapshot.get("period")
    return PortfolioResponse(
        account=AccountSnapshotDTO(**snapshot["account"]),
        positions=[PositionSnapshotDTO(**row) for row in snapshot["positions"]],
        deployment_positions=[
            DeploymentPositionSnapshotDTO(**row) for row in snapshot["deployment_positions"]
        ],
        untracked_positions=[
            UntrackedPositionSnapshotDTO(**row) for row in snapshot["untracked_positions"]
        ],
        position_rows=[PortfolioPositionRowDTO(**row) for row in snapshot.get("position_rows", [])],
        summary=PortfolioSummaryDTO(**summary) if summary else None,
        period=PortfolioPeriodDTO(**period) if period else None,
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


@router.get("/overview", response_model=DeploymentOverviewResponse)
async def get_overview(
    session: AsyncSession = Depends(get_db),
) -> DeploymentOverviewResponse:
    try:
        rows = await get_deployment_overview(session)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return DeploymentOverviewResponse(deployments=[_overview_dto(row) for row in rows])


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


@router.delete("/deployments/{deployment_id}", response_model=DeleteDeploymentResponse)
async def delete_deployment_route(
    deployment_id: UUID,
    body: DeleteDeploymentRequest,
    session: AsyncSession = Depends(get_db),
) -> DeleteDeploymentResponse:
    try:
        result = await delete_deployment(
            session,
            deployment_id,
            close_positions=body.close_positions,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in detail.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return DeleteDeploymentResponse(**result)


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
        explainability=_explainability_dto(result.get("explainability")),
        warnings=result.get("warnings") or [],
        order=result.get("order"),
        blocked_reason=result.get("blocked_reason"),
        outcome=result.get("outcome"),
        error=result.get("error"),
    )


@router.post("/deployments/{deployment_id}/refresh", response_model=DeploymentRefreshResponse)
async def refresh_deployment_route(
    deployment_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> DeploymentRefreshResponse:
    row = await get_deployment(session, deployment_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deployment_id}")
    try:
        result = await refresh_deployment_market_data(session, row)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return DeploymentRefreshResponse(
        deployment_id=deployment_id,
        results=result.get("results") or [],
    )


@router.post(
    "/deployments/{deployment_id}/evaluate/enqueue",
    response_model=EnqueueJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_evaluate_deployment(
    deployment_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> EnqueueJobResponse:
    row = await get_deployment(session, deployment_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deployment_id}")
    job = await create_and_enqueue_job(
        session,
        "execution_evaluate_one",
        {"deployment_id": str(deployment_id)},
    )
    return EnqueueJobResponse(job_id=str(job["id"]), status=job["status"])


@router.post("/evaluate-all", response_model=EvaluateAllResponse)
async def evaluate_all_route(
    session: AsyncSession = Depends(get_db),
) -> EvaluateAllResponse:
    try:
        result = await evaluate_all_active(session)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return EvaluateAllResponse(**result)


@router.post("/evaluate-all/enqueue", response_model=EnqueueJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_evaluate_all(
    session: AsyncSession = Depends(get_db),
) -> EnqueueJobResponse:
    job = await create_and_enqueue_job(session, "execution_evaluate_all", {})
    return EnqueueJobResponse(job_id=str(job["id"]), status=job["status"])


@router.post(
    "/market-data/refresh/enqueue",
    response_model=EnqueueJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_market_data_refresh(
    session: AsyncSession = Depends(get_db),
) -> EnqueueJobResponse:
    job = await create_and_enqueue_job(session, "deployment_market_data_refresh", {})
    return EnqueueJobResponse(job_id=str(job["id"]), status=job["status"])


@router.post(
    "/deployment-cycle/enqueue",
    response_model=EnqueueJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_deployment_cycle(
    body: DeploymentCycleEnqueueRequest | None = None,
    session: AsyncSession = Depends(get_db),
) -> EnqueueJobResponse:
    params: dict = {}
    if body and body.scheduled_at:
        params["scheduled_at"] = body.scheduled_at.isoformat()
    job = await create_and_enqueue_job(session, "execution_deployment_cycle", params)
    return EnqueueJobResponse(job_id=str(job["id"]), status=job["status"])


@router.post(
    "/reconciliation/enqueue",
    response_model=EnqueueJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_reconciliation(
    session: AsyncSession = Depends(get_db),
) -> EnqueueJobResponse:
    job = await create_and_enqueue_job(session, "execution_deployment_reconciliation", {})
    return EnqueueJobResponse(job_id=str(job["id"]), status=job["status"])


@router.post("/reconciliation", response_model=ReconciliationResponse)
async def run_reconciliation(
    session: AsyncSession = Depends(get_db),
) -> ReconciliationResponse:
    result = await reconcile_missed_updates(session)
    return ReconciliationResponse(**result)


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
