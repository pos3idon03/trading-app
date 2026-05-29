from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from dtos.backtest_dto import BacktestEquityPointDTO, BacktestMetricsDTO, BacktestTradeDTO
from dtos.foundation_backtest_dto import (
    FoundationBacktestResultsResponse,
    FoundationForecastMetricsDTO,
    FoundationForecastPointDTO,
    FoundationJobAcceptedResponse,
    FoundationModelCatalogItemDTO,
    FoundationModelCatalogResponse,
    FoundationParamConstraintDTO,
    FoundationPreviewRequest,
    FoundationPreviewResponse,
    FoundationRunRequest,
    FoundationSummaryDTO,
    FoundationWalkForwardMetaDTO,
)
from features.foundation.availability import foundation_models_available, foundation_models_enabled
from features.foundation.orchestrator import (
    get_foundation_catalog,
    get_foundation_backtest_results,
)
from features.worker.tasks import create_and_enqueue_job

router = APIRouter(prefix="/backtest/foundation", tags=["backtest-foundation"])


def _require_foundation_route() -> None:
    if not foundation_models_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Foundation models are disabled. Set FOUNDATION_MODELS_ENABLED=true.",
        )
    if not foundation_models_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Foundation model dependencies are not installed. "
                "Install tiingo_backend/requirements-foundation.txt "
                "(TimesFM requires git; see FOUNDATION_MANUAL.md)."
            ),
        )


@router.get("/models", response_model=FoundationModelCatalogResponse)
async def list_foundation_models() -> FoundationModelCatalogResponse:
    if not foundation_models_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Foundation models are disabled. Set FOUNDATION_MODELS_ENABLED=true.",
        )
    items = []
    for row in get_foundation_catalog():
        constraints = {
            key: FoundationParamConstraintDTO(min=bounds[0], max=bounds[1])
            for key, bounds in row.get("constraints", {}).items()
        }
        items.append(
            FoundationModelCatalogItemDTO(
                id=row["id"],
                label=row["label"],
                description=row["description"],
                params=row["params"],
                constraints=constraints,
            )
        )
    return FoundationModelCatalogResponse(models=items)


@router.post("/preview", status_code=status.HTTP_202_ACCEPTED, response_model=FoundationJobAcceptedResponse)
async def foundation_preview(
    body: FoundationPreviewRequest,
    session: AsyncSession = Depends(get_db),
) -> FoundationJobAcceptedResponse:
    _require_foundation_route()
    job = await create_and_enqueue_job(
        session,
        "foundation_preview",
        body.model_dump(mode="json"),
    )
    return FoundationJobAcceptedResponse(job_id=job["id"])


@router.post("/run", status_code=status.HTTP_202_ACCEPTED, response_model=FoundationJobAcceptedResponse)
async def run_foundation_backtest(
    body: FoundationRunRequest,
    session: AsyncSession = Depends(get_db),
) -> FoundationJobAcceptedResponse:
    _require_foundation_route()
    job = await create_and_enqueue_job(
        session,
        "foundation_backtest",
        body.model_dump(mode="json"),
    )
    return FoundationJobAcceptedResponse(job_id=job["id"])


@router.get("/{run_id}/results", response_model=FoundationBacktestResultsResponse)
async def get_foundation_backtest_run_results(
    run_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> FoundationBacktestResultsResponse:
    row = await get_foundation_backtest_results(session, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Foundation backtest run not found: {run_id}")

    benchmark_curve = []
    if row.get("benchmark") and row["benchmark"].get("equity_curve"):
        benchmark_curve = [
            BacktestEquityPointDTO(**point) for point in row["benchmark"]["equity_curve"]
        ]

    summary_raw = row.get("foundation_summary")
    foundation_summary = None
    if summary_raw:
        walk_raw = summary_raw.get("walk_forward") or {}
        metrics_raw = summary_raw.get("forecast_metrics") or {}
        foundation_summary = FoundationSummaryDTO(
            model_type=summary_raw.get("model_type", row["strategy"]),
            signal_counts=summary_raw.get("signal_counts") or {},
            forecast_metrics=FoundationForecastMetricsDTO(**metrics_raw),
            walk_forward=FoundationWalkForwardMetaDTO(**walk_raw),
            simulation_start_bar_index=summary_raw.get("simulation_start_bar_index"),
            simulation_start_date=summary_raw.get("simulation_start_date"),
            pre_oos_bars_excluded=summary_raw.get("pre_oos_bars_excluded"),
            forecast_samples=[
                FoundationForecastPointDTO(**point)
                for point in (summary_raw.get("forecast_samples") or [])
            ],
        )

    return FoundationBacktestResultsResponse(
        id=row["id"],
        symbol=row["symbol"],
        model_type=row["strategy"],
        params=row.get("params") or {},
        timeframe=row["timeframe"],
        start_date=row.get("start_date"),
        end_date=row.get("end_date"),
        initial_cash=float(row["initial_cash"]),
        commission_bps=float(row["commission_bps"]),
        status=row["status"],
        metrics=BacktestMetricsDTO(**row["metrics"]) if row.get("metrics") else None,
        equity_curve=[BacktestEquityPointDTO(**point) for point in (row.get("equity_curve") or [])],
        benchmark_equity_curve=benchmark_curve,
        trades=[BacktestTradeDTO(**trade) for trade in (row.get("trades") or [])],
        foundation_summary=foundation_summary,
        error_message=row.get("error_message"),
        created_at=row["created_at"],
        finished_at=row.get("finished_at"),
    )
