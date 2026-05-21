from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import instrument_dal
from db import get_db
from dtos.market_data_dto import (
    InstrumentCreateRequest,
    InstrumentCreateResponse,
    InstrumentDTO,
    InstrumentPatchRequest,
    TickerSearchResponseDTO,
)
from features.tiingo.search_client import search_tickers
from features.worker.tasks import create_and_enqueue_job

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/search", response_model=TickerSearchResponseDTO)
async def instrument_search(
    query: str = Query(..., min_length=2, description="Search by name or ticker via Tiingo"),
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
) -> TickerSearchResponseDTO:
    return await search_tickers(query=query, limit=limit, session=session)


@router.get("/db-search", response_model=list[InstrumentDTO])
async def db_instrument_search(
    query: str = Query(..., min_length=1, description="Search ingested instruments in database"),
    asset_type: list[str] = Query(default=[]),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    types = asset_type or None
    return await instrument_dal.search_instruments(
        session, query, asset_types=types, limit=limit
    )


@router.get("", response_model=list[InstrumentDTO])
async def list_instruments(active_only: bool = False, session: AsyncSession = Depends(get_db)):
    return await instrument_dal.list_instruments(session, active_only=active_only)


@router.post("", response_model=InstrumentCreateResponse, status_code=201)
async def create_instrument(
    body: InstrumentCreateRequest,
    session: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    instrument = await instrument_dal.upsert_instrument(session, body.model_dump(exclude={"auto_ingest"}))
    job_id = None

    should_ingest = (
        body.auto_ingest
        and settings.auto_backfill_on_create
        and instrument.get("is_active", True)
    )
    if should_ingest:
        job = await create_and_enqueue_job(
            session,
            "asset_full_ingest",
            {"symbol": instrument["symbol"]},
        )
        job_id = job["id"]

    return InstrumentCreateResponse(**instrument, job_id=job_id)


@router.patch("/{symbol}", response_model=InstrumentDTO)
async def patch_instrument(
    symbol: str,
    body: InstrumentPatchRequest,
    session: AsyncSession = Depends(get_db),
):
    result = await instrument_dal.patch_instrument(session, symbol, body.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(404, "Instrument not found")
    return result


@router.delete("/{symbol}", status_code=204)
async def delete_instrument(symbol: str, session: AsyncSession = Depends(get_db)):
    if not await instrument_dal.delete_instrument(session, symbol):
        raise HTTPException(404, "Instrument not found")
