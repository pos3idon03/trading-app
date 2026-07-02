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
    MlWorkbookExportRequest,
)
from dtos.rl_backtest_dto import MlUniverseRunRequest, UniverseListResponse
from dal import universe_dal
from features.ml.orchestrator import (
    delete_saved_ml_model,
    get_ml_backtest_results,
    get_ml_model_catalog,
    get_saved_ml_model,
    list_saved_ml_models,
)
from features.ml.universe_orchestrator import run_universe_ml_backtest
from features.ml.saved_model_metadata import extract_saved_model_metadata
from features.worker.tasks import create_and_enqueue_job

router = APIRouter(prefix="/backtest/ml", tags=["backtest-ml"])


def _saved_model_dto(row: dict) -> MlSavedModelDTO:
    metadata = extract_saved_model_metadata(row)
    return MlSavedModelDTO(
        id=row["id"],
        name=row["name"],
        model_type=row["model_type"],
        feature_mode=row["feature_mode"],
        feature_schema=row.get("feature_schema") or {},
        hyperparams=row.get("hyperparams") or {},
        train_metrics=row.get("train_metrics"),
        symbol=metadata["symbol"],
        timeframe=metadata["timeframe"],
        created_at=row["created_at"],
    )


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
    return MlSavedModelsResponse(models=[_saved_model_dto(row) for row in rows])


@router.get("/saved-models/{model_id}", response_model=MlSavedModelDTO)
async def get_saved_model(
    model_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> MlSavedModelDTO:
    row = await get_saved_ml_model(session, model_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Saved model not found: {model_id}")
    return _saved_model_dto(row)


@router.delete("/saved-models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_model(
    model_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    try:
        await delete_saved_ml_model(session, model_id)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Saved model not found: {model_id}") from None


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


@router.post("/workbook-export", status_code=status.HTTP_202_ACCEPTED, response_model=MlJobAcceptedResponse)
async def ml_workbook_export(
    body: MlWorkbookExportRequest,
    session: AsyncSession = Depends(get_db),
) -> MlJobAcceptedResponse:
    job = await create_and_enqueue_job(
        session,
        "ml_workbook_export",
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


@router.get("/universes", response_model=UniverseListResponse)
async def list_universes(
    session: AsyncSession = Depends(get_db),
) -> UniverseListResponse:
    rows = await universe_dal.list_universes(session)
    from dtos.rl_backtest_dto import UniverseDefinitionDTO

    return UniverseListResponse(
        universes=[
            UniverseDefinitionDTO(
                id=r["id"],
                name=r["name"],
                source=r.get("source"),
                description=r.get("description"),
            )
            for r in rows
        ]
    )


@router.post("/universe/run")
async def run_universe_backtest(
    body: MlUniverseRunRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    try:
        result = await run_universe_ml_backtest(
            session,
            universe_id=body.universe_id,
            symbols=body.symbols or None,
            signals_by_symbol=body.signals_by_symbol,
            timeframe=body.timeframe,
            start=body.start,
            end=body.end,
            initial_cash=body.initial_cash,
            commission_bps=body.commission_bps,
            slippage_bps=body.slippage_bps,
            sizing_params=body.sizing_params,
        )
        sim = result["simulation"]
        return {
            "symbols": result["symbols"],
            "final_equity": sim.final_equity,
            "trades": [t.__dict__ for t in sim.trades],
            "equity_curve": [p.__dict__ for p in sim.equity_curve],
            "survivorship_warnings": result["survivorship_warnings"],
            "target_weights": result["target_weights"],
        }
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
