from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from db import get_db
from dal import rl_model_dal
from dtos.rl_backtest_dto import (
    RlModelCatalogResponse,
    RlRunRequest,
    RlRunResponse,
    RlSavedModelDTO,
    RlSavedModelsResponse,
    RlTrainRequest,
    RlTrainResponse,
)
from features.backtesting.engine import run_backtest_with_signals
from features.backtesting.metrics import compute_backtest_metrics
from features.rl.catalog import list_rl_models, validate_rl_params
from features.rl.inference import run_rl_inference_for_symbol
from features.rl.orchestrator import persist_rl_model, train_rl_agent_for_symbol

router = APIRouter(prefix="/backtest/rl", tags=["backtest-rl"])


@router.get("/models", response_model=RlModelCatalogResponse)
async def list_models() -> RlModelCatalogResponse:
    return RlModelCatalogResponse(models=list_rl_models())


@router.get("/saved-models", response_model=RlSavedModelsResponse)
async def list_saved_models(
    session: AsyncSession = Depends(get_db),
) -> RlSavedModelsResponse:
    rows = await rl_model_dal.list_models(session)
    return RlSavedModelsResponse(
        models=[
            RlSavedModelDTO(
                id=row["id"],
                name=row["name"],
                model_type=row["model_type"],
                symbol=row.get("symbol"),
                timeframe=row["timeframe"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
    )


@router.post("/train", response_model=RlTrainResponse)
async def train_rl(
    body: RlTrainRequest,
    session: AsyncSession = Depends(get_db),
) -> RlTrainResponse:
    try:
        validate_rl_params(body.model_type, body.params)
        result = await train_rl_agent_for_symbol(
            session,
            symbol=body.symbol,
            model_type=body.model_type,
            params=body.params,
            timeframe=body.timeframe,
            start=body.start,
            end=body.end,
        )
        model_id = await persist_rl_model(
            session,
            name=body.name or f"{body.symbol} DDQN",
            train_result=result,
        )
        await session.commit()
        return RlTrainResponse(
            id=model_id,
            name=body.name or f"{body.symbol} DDQN",
            model_type=body.model_type,
            train_metrics=result["train_metrics"],
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/run", response_model=RlRunResponse)
async def run_rl(
    body: RlRunRequest,
    session: AsyncSession = Depends(get_db),
) -> RlRunResponse:
    try:
        if body.model_id:
            inference = await run_rl_inference_for_symbol(
                session,
                model_id=UUID(str(body.model_id)),
                symbol=body.symbol,
                timeframe=body.timeframe,
                start=body.start,
                end=body.end,
                params=body.params,
            )
            sim = run_backtest_with_signals(
                inference["bars"],
                inference["signals"],
                initial_cash=10_000.0,
                commission_bps=float(inference["hyperparams"].get("commission_bps", 5.0)),
                decision_timeframe=body.timeframe,
                slippage_bps=float(inference["hyperparams"].get("slippage_bps", 0.0)),
            )
            metrics = compute_backtest_metrics(sim, inference["bars"], decision_timeframe=body.timeframe)
            return RlRunResponse(
                symbol=body.symbol.upper(),
                model_type=body.model_type,
                metrics=metrics,
                train_reward=0.0,
                model_id=body.model_id,
            )

        result = await train_rl_agent_for_symbol(
            session,
            symbol=body.symbol,
            model_type=body.model_type,
            params=body.params,
            timeframe=body.timeframe,
            start=body.start,
            end=body.end,
        )
        return RlRunResponse(
            symbol=body.symbol.upper(),
            model_type=body.model_type,
            metrics=result["metrics"],
            train_reward=result["train_reward"],
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
