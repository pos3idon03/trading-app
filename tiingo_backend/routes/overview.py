from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from dtos.market_data_dto import (
    AssetOverviewResponseDTO,
    AssetOverviewRowDTO,
    MacroOverviewResponseDTO,
    MacroOverviewRowDTO,
    MetricGrowthDTO,
)
from features.market_data.overview_assets import load_asset_overview
from features.market_data.overview_macro import load_macro_overview

router = APIRouter(prefix="/market-data/overview", tags=["overview"])

_VALID_ASSET_TYPES = {"stock", "etf", "crypto"}
_VALID_CATEGORIES = {"all", "inflation", "labor", "rates", "housing", "energy", "goods"}


def _growth_dto(data: dict | None) -> MetricGrowthDTO | None:
    if not data:
        return None
    return MetricGrowthDTO(
        latest_period=data.get("latest_period"),
        yoy=data.get("yoy"),
        qoq=data.get("qoq"),
        cagr=data.get("cagr"),
    )


def _asset_row_dto(row: dict) -> AssetOverviewRowDTO:
    return AssetOverviewRowDTO(
        symbol=row["symbol"],
        name=row.get("name"),
        as_of=row.get("as_of"),
        pe_ratio=row.get("pe_ratio"),
        dividend_yield=row.get("dividend_yield"),
        debt_equity=row.get("debt_equity"),
        current_ratio=row.get("current_ratio"),
        eps_ttm=row.get("eps_ttm"),
        revenue_growth=_growth_dto(row.get("revenue_growth")),
        ebitda_growth=_growth_dto(row.get("ebitda_growth")),
        ocf_growth=_growth_dto(row.get("ocf_growth")),
        price_change_6m=row.get("price_change_6m"),
        performance=row.get("performance"),
    )


@router.get("/assets", response_model=AssetOverviewResponseDTO)
async def get_asset_overview(
    asset_type: str = Query(...),
    session: AsyncSession = Depends(get_db),
) -> AssetOverviewResponseDTO:
    normalized = asset_type.lower()
    if normalized not in _VALID_ASSET_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"asset_type must be one of: {sorted(_VALID_ASSET_TYPES)}",
        )

    payload = await load_asset_overview(session, normalized)
    return AssetOverviewResponseDTO(
        asset_type=payload["asset_type"],
        as_of=payload["as_of"],
        rows=[_asset_row_dto(row) for row in payload["rows"]],
    )


@router.get("/macro", response_model=MacroOverviewResponseDTO)
async def get_macro_overview(
    category: str = Query(default="all"),
    session: AsyncSession = Depends(get_db),
) -> MacroOverviewResponseDTO:
    normalized = category.lower()
    if normalized not in _VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"category must be one of: {sorted(_VALID_CATEGORIES)}",
        )

    try:
        payload = await load_macro_overview(session, normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MacroOverviewResponseDTO(
        category=payload["category"],
        as_of=payload["as_of"],
        rows=[MacroOverviewRowDTO(**row) for row in payload["rows"]],
    )
