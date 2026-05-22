from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from dtos.backtest_dto import (
    BacktestEquityPointDTO,
    BacktestMetricsDTO,
    BacktestResultsResponse,
    BacktestRunRequest,
    BacktestRunResponse,
    BacktestTradeDTO,
    StrategyCatalogItemDTO,
    StrategyCatalogResponse,
    StrategyParamConstraintDTO,
)
from features.backtesting.orchestrator import get_backtest_results, get_strategy_catalog, run_backtest_for_symbol

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("/strategies", response_model=StrategyCatalogResponse)
async def list_backtest_strategies() -> StrategyCatalogResponse:
    items = []
    for row in get_strategy_catalog():
        constraints = {
            key: StrategyParamConstraintDTO(min=bounds[0], max=bounds[1])
            for key, bounds in row.get("constraints", {}).items()
        }
        items.append(
            StrategyCatalogItemDTO(
                id=row["id"],
                label=row["label"],
                description=row["description"],
                params=row["params"],
                constraints=constraints,
                ensemble_eligible=row.get("ensemble_eligible", False),
            )
        )
    return StrategyCatalogResponse(strategies=items)


@router.post("/run", response_model=BacktestRunResponse)
async def run_backtest(
    body: BacktestRunRequest,
    session: AsyncSession = Depends(get_db),
) -> BacktestRunResponse:
    try:
        result = await run_backtest_for_symbol(
            session,
            symbol=body.symbol,
            strategy=body.strategy,
            params=body.params,
            timeframe=body.timeframe,
            signal_timeframe=body.signal_timeframe,
            start=body.start,
            end=body.end,
            initial_cash=body.initial_cash,
            commission_bps=body.commission_bps,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return BacktestRunResponse(
        id=result["id"],
        symbol=result["symbol"],
        strategy=result["strategy"],
        status=result["status"],
        metrics=BacktestMetricsDTO(**result["metrics"]) if result.get("metrics") else None,
    )


@router.get("/{run_id}/results", response_model=BacktestResultsResponse)
async def get_backtest_run_results(
    run_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> BacktestResultsResponse:
    row = await get_backtest_results(session, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Backtest run not found: {run_id}")

    benchmark_curve = []
    if row.get("benchmark") and row["benchmark"].get("equity_curve"):
        benchmark_curve = [
            BacktestEquityPointDTO(**point) for point in row["benchmark"]["equity_curve"]
        ]

    return BacktestResultsResponse(
        id=row["id"],
        symbol=row["symbol"],
        strategy=row["strategy"],
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
        error_message=row.get("error_message"),
        created_at=row["created_at"],
        finished_at=row.get("finished_at"),
    )
