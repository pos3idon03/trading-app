from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dal import fundamentals_dal, instrument_dal
from db import get_db
from dtos.market_data_dto import (
    FundamentalMetricDTO,
    FundamentalsCoverageItemDTO,
    FundamentalsCoverageResponseDTO,
    FundamentalsMetricsResponseDTO,
)

router = APIRouter(prefix="/ingestion/fundamentals", tags=["fundamentals"])

_VALID_PERIOD_TYPES = frozenset({"quarterly", "annual"})


@router.get("/coverage", response_model=FundamentalsCoverageResponseDTO)
async def list_fundamentals_coverage(
    session: AsyncSession = Depends(get_db),
) -> FundamentalsCoverageResponseDTO:
    rows = await fundamentals_dal.list_fundamentals_coverage(session)
    items = [FundamentalsCoverageItemDTO(**row) for row in rows]
    return FundamentalsCoverageResponseDTO(items=items, count=len(items))


@router.get("/{symbol}", response_model=FundamentalsMetricsResponseDTO)
async def get_fundamentals(
    symbol: str,
    period_type: str = Query(default="quarterly"),
    metric_names: str | None = Query(default=None),
    order: str = Query(default="asc"),
    limit: int = Query(default=10000, ge=1, le=10000),
    all: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
) -> FundamentalsMetricsResponseDTO:
    if period_type not in _VALID_PERIOD_TYPES:
        raise HTTPException(400, "period_type must be 'quarterly' or 'annual'")
    if order not in ("asc", "desc"):
        raise HTTPException(400, "order must be 'asc' or 'desc'")

    inst = await instrument_dal.get_by_symbol(session, symbol)
    if not inst:
        raise HTTPException(404, "Instrument not found")

    names = [n.strip() for n in metric_names.split(",") if n.strip()] if metric_names else None
    effective_limit = None if all else limit
    rows = await fundamentals_dal.list_fundamentals_for_symbol(
        session,
        inst["id"],
        period_type=period_type,
        metric_names=names,
        order=order,
        limit=effective_limit,
    )
    if not rows:
        raise HTTPException(404, f"No fundamentals found for {symbol.upper()}")

    metrics = [FundamentalMetricDTO(**row) for row in rows]
    return FundamentalsMetricsResponseDTO(
        symbol=symbol.upper(),
        period_type=period_type,
        metrics=metrics,
        count=len(metrics),
    )
