from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dal import job_dal, macro_dal
from db import get_db
from dtos.market_data_dto import MacroBackfillRequest, MacroSeriesDTO
from features.fred.macro_orchestrator import backfill_series, seed_catalog
from features.ingestion.job_runner import execute_job

router = APIRouter(prefix="/ingestion/macro", tags=["macro"])


@router.get("/series", response_model=list[MacroSeriesDTO])
async def list_macro_series(session: AsyncSession = Depends(get_db)):
    await seed_catalog(session)
    return await macro_dal.list_series(session)


@router.post("/backfill", status_code=202)
async def macro_backfill(
    body: MacroBackfillRequest,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    await seed_catalog(session)
    job = await job_dal.create_job(session, "macro_backfill", body.model_dump())
    background.add_task(execute_job, job["id"], "macro_backfill", body.model_dump())
    return {"job_id": str(job["id"]), "status": "accepted"}


@router.post("/refresh", status_code=202)
async def macro_refresh(background: BackgroundTasks, session: AsyncSession = Depends(get_db)):
    job = await job_dal.create_job(session, "macro_refresh", {})
    background.add_task(execute_job, job["id"], "macro_refresh", {})
    return {"job_id": str(job["id"]), "status": "accepted"}


@router.get("/observations/{series_id}")
async def macro_observations(
    series_id: str,
    limit: int = 120,
    order: str = "desc",
    session: AsyncSession = Depends(get_db),
):
    if order not in ("asc", "desc"):
        raise HTTPException(400, "order must be 'asc' or 'desc'")
    obs = await macro_dal.get_observations(session, series_id, limit, order=order)
    if not obs:
        raise HTTPException(404, "No observations found")
    return {"series_id": series_id, "observations": obs}
