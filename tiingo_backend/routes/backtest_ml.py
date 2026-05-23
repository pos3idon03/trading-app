from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from dtos.backtest_dto import BacktestEquityPointDTO, BacktestMetricsDTO, BacktestTradeDTO
from dtos.ml_backtest_dto import (
    MlBacktestResultsResponse,
    MlDataPreviewRequest,
    MlHyperparameterSearchRequest,
    MlJobAcceptedResponse,
    MlLabelSearchRequest,
    MlModelCatalogItemDTO,
    MlModelCatalogResponse,
    MlParamConstraintDTO,
    MlRunRequest,
    MlSavedModelDTO,
    MlSavedModelsResponse,
    MlSummaryDTO,
    MlThresholdSearchRequest,
    MlTrainRequest,
    MlTrainingExportRequest,
)
from features.ml.orchestrator import (
    get_ml_backtest_results,
    get_ml_model_catalog,
    get_saved_ml_model,
    list_saved_ml_models,
)
from features.worker.tasks import create_and_enqueue_job

router = APIRouter(prefix="/backtest/ml", tags=["backtest-ml"])


@router.get("/models", response_model=MlModelCatalogResponse)
async def list_ml_models() -> MlModelCatalogResponse:
    items = []
    for row in get_ml_model_catalog():
        constraints = {
            key: MlParamConstraintDTO(min=bounds[0], max=bounds[1])
            for key, bounds in row.get("constraints", {}).items()
        }
        items.append(
            MlModelCatalogItemDTO(
                id=row["id"],
                label=row["label"],
                description=row["description"],
                params=row["params"],
                constraints=constraints,
                supports_hyperparameter_search=row.get("supports_hyperparameter_search", False),
            )
        )
    return MlModelCatalogResponse(models=items)


@router.get("/saved-models", response_model=MlSavedModelsResponse)
async def list_saved_models(
    session: AsyncSession = Depends(get_db),
) -> MlSavedModelsResponse:
    rows = await list_saved_ml_models(session)
    return MlSavedModelsResponse(
        models=[
            MlSavedModelDTO(
                id=row["id"],
                name=row["name"],
                model_type=row["model_type"],
                feature_mode=row["feature_mode"],
                feature_schema=row.get("feature_schema") or {},
                hyperparams=row.get("hyperparams") or {},
                train_metrics=row.get("train_metrics"),
                created_at=row["created_at"],
            )
            for row in rows
        ]
    )


@router.get("/saved-models/{model_id}", response_model=MlSavedModelDTO)
async def get_saved_model(
    model_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> MlSavedModelDTO:
    row = await get_saved_ml_model(session, model_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Saved model not found: {model_id}")
    return MlSavedModelDTO(
        id=row["id"],
        name=row["name"],
        model_type=row["model_type"],
        feature_mode=row["feature_mode"],
        feature_schema=row.get("feature_schema") or {},
        hyperparams=row.get("hyperparams") or {},
        train_metrics=row.get("train_metrics"),
        created_at=row["created_at"],
    )


@router.post("/data-preview", status_code=status.HTTP_202_ACCEPTED, response_model=MlJobAcceptedResponse)
async def ml_data_preview(
    body: MlDataPreviewRequest,
    session: AsyncSession = Depends(get_db),
) -> MlJobAcceptedResponse:
    job = await create_and_enqueue_job(
        session,
        "ml_data_preview",
        body.model_dump(mode="json"),
    )
    return MlJobAcceptedResponse(job_id=job["id"])


@router.post("/label-search", status_code=status.HTTP_202_ACCEPTED, response_model=MlJobAcceptedResponse)
async def ml_label_search(
    body: MlLabelSearchRequest,
    session: AsyncSession = Depends(get_db),
) -> MlJobAcceptedResponse:
    job = await create_and_enqueue_job(
        session,
        "ml_label_search",
        body.model_dump(mode="json"),
    )
    return MlJobAcceptedResponse(job_id=job["id"])


@router.post("/threshold-search", status_code=status.HTTP_202_ACCEPTED, response_model=MlJobAcceptedResponse)
async def ml_threshold_search(
    body: MlThresholdSearchRequest,
    session: AsyncSession = Depends(get_db),
) -> MlJobAcceptedResponse:
    job = await create_and_enqueue_job(
        session,
        "ml_threshold_search",
        body.model_dump(mode="json"),
    )
    return MlJobAcceptedResponse(job_id=job["id"])


@router.post("/hyperparameter-search", status_code=status.HTTP_202_ACCEPTED, response_model=MlJobAcceptedResponse)
async def ml_hyperparameter_search(
    body: MlHyperparameterSearchRequest,
    session: AsyncSession = Depends(get_db),
) -> MlJobAcceptedResponse:
    job = await create_and_enqueue_job(
        session,
        "ml_hyperparameter_search",
        body.model_dump(mode="json"),
    )
    return MlJobAcceptedResponse(job_id=job["id"])


@router.post("/training-data-export", status_code=status.HTTP_202_ACCEPTED, response_model=MlJobAcceptedResponse)
async def ml_training_data_export(
    body: MlTrainingExportRequest,
    session: AsyncSession = Depends(get_db),
) -> MlJobAcceptedResponse:
    job = await create_and_enqueue_job(
        session,
        "ml_training_export",
        body.model_dump(mode="json"),
    )
    return MlJobAcceptedResponse(job_id=job["id"])


@router.post("/train", status_code=status.HTTP_202_ACCEPTED, response_model=MlJobAcceptedResponse)
async def train_ml_model(
    body: MlTrainRequest,
    session: AsyncSession = Depends(get_db),
) -> MlJobAcceptedResponse:
    job = await create_and_enqueue_job(
        session,
        "ml_train",
        body.model_dump(mode="json"),
    )
    return MlJobAcceptedResponse(job_id=job["id"])


@router.post("/run", status_code=status.HTTP_202_ACCEPTED, response_model=MlJobAcceptedResponse)
async def run_ml_backtest(
    body: MlRunRequest,
    session: AsyncSession = Depends(get_db),
) -> MlJobAcceptedResponse:
    job = await create_and_enqueue_job(
        session,
        "ml_backtest",
        body.model_dump(mode="json"),
    )
    return MlJobAcceptedResponse(job_id=job["id"])


@router.get("/{run_id}/results", response_model=MlBacktestResultsResponse)
async def get_ml_backtest_run_results(
    run_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> MlBacktestResultsResponse:
    row = await get_ml_backtest_results(session, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"ML backtest run not found: {run_id}")

    benchmark_curve = []
    if row.get("benchmark") and row["benchmark"].get("equity_curve"):
        benchmark_curve = [
            BacktestEquityPointDTO(**point) for point in row["benchmark"]["equity_curve"]
        ]

    ml_summary_raw = row.get("ml_summary")
    ml_summary = MlSummaryDTO(**ml_summary_raw) if ml_summary_raw else None

    return MlBacktestResultsResponse(
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
        ml_summary=ml_summary,
        error_message=row.get("error_message"),
        created_at=row["created_at"],
        finished_at=row.get("finished_at"),
    )
