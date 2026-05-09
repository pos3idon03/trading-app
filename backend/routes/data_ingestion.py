import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_asset_id_by_symbol, get_ohlcv, list_assets
from db import get_db
from dtos.market_data_dto import (
    AssetDTO,
    AssetListResponse,
    IngestRequest,
    IngestResponse,
    IngestionStatusResponse,
    OHLCVQueryResponse,
    OHLCVRecord,
    TickerSearchResponse,
)
from features.data_ingestion.ingest_service import run_ingest_job
from features.data_ingestion.scheduler import list_jobs
from features.data_ingestion.ticker_search import search_tickers
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse, status_code=202)
async def trigger_ingestion(
    request: IngestRequest,
    session: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Trigger manual data ingestion for specified symbols and timeframes."""
    job_id = str(uuid.uuid4())
    logger.info("ingest_triggered", job_id=job_id, symbols=request.symbols)

    try:
        results = await run_ingest_job(session, request)
        errors = [r for r in results if r.get("status") == "error"]
        status = "partial_error" if errors else "completed"
    except Exception as exc:
        logger.error("ingest_job_failed", job_id=job_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return IngestResponse(
        job_id=job_id,
        status=status,
        symbols=request.symbols,
        timeframes=request.timeframes,
        message=f"Ingestion {status}: {len(results)} tasks processed",
    )


@router.get("/assets", response_model=AssetListResponse)
async def get_assets(
    session: AsyncSession = Depends(get_db),
) -> AssetListResponse:
    """Return all assets that have been ingested."""
    rows = await list_assets(session)
    assets = [AssetDTO(**row) for row in rows]
    return AssetListResponse(assets=assets, count=len(assets))


@router.get("/ohlcv/by-symbol/{symbol}", response_model=OHLCVQueryResponse)
async def get_ohlcv_by_symbol(
    symbol: str,
    timeframe: str = Query(default="1d"),
    start: datetime = Query(default=None),
    end: datetime = Query(default=None),
    bucket: Optional[str] = Query(default=None, description="TimescaleDB bucket e.g. '1 hour'"),
    session: AsyncSession = Depends(get_db),
) -> OHLCVQueryResponse:
    """Retrieve stored OHLCV data for a ticker symbol."""
    from utils.time_utils import utcnow

    symbol = symbol.upper()
    asset_id = await get_asset_id_by_symbol(session, symbol)
    if asset_id is None:
        raise HTTPException(status_code=404, detail=f"Asset not found: {symbol}")

    if start is None:
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    if end is None:
        end = utcnow()

    df = await get_ohlcv(session, asset_id, timeframe, start, end, bucket_interval=bucket)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No OHLCV data found for {symbol} ({timeframe})")

    records = _build_ohlcv_records(df, asset_id, timeframe)
    return OHLCVQueryResponse(
        asset_id=asset_id,
        symbol=symbol,
        timeframe=timeframe,
        records=records,
        count=len(records),
    )


@router.get("/ohlcv/{asset_id}", response_model=OHLCVQueryResponse)
async def get_ohlcv_data(
    asset_id: int,
    timeframe: str = Query(default="1d"),
    start: datetime = Query(default=None),
    end: datetime = Query(default=None),
    bucket: Optional[str] = Query(default=None, description="TimescaleDB bucket e.g. '1 hour'"),
    session: AsyncSession = Depends(get_db),
) -> OHLCVQueryResponse:
    """Retrieve stored OHLCV data for an asset by numeric ID."""
    from utils.time_utils import utcnow
    if start is None:
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    if end is None:
        end = utcnow()

    df = await get_ohlcv(session, asset_id, timeframe, start, end, bucket_interval=bucket)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No OHLCV data found for asset_id={asset_id}")

    symbol = await _resolve_symbol(session, asset_id)
    records = _build_ohlcv_records(df, asset_id, timeframe)
    return OHLCVQueryResponse(
        asset_id=asset_id,
        symbol=symbol,
        timeframe=timeframe,
        records=records,
        count=len(records),
    )


def _build_ohlcv_records(df, asset_id: int, timeframe: str) -> list[OHLCVRecord]:
    return [
        OHLCVRecord(
            time=row["time"],
            asset_id=asset_id,
            timeframe=timeframe,
            open=row["open"], high=row["high"], low=row["low"], close=row["close"],
            volume=int(row.get("volume", 0)),
            vwap=row.get("vwap"),
            source=row.get("source", "unknown"),
        )
        for _, row in df.iterrows()
    ]


async def _resolve_symbol(session, asset_id: int) -> str:
    from models.asset import Asset
    from sqlalchemy import select
    stmt = select(Asset.symbol).where(Asset.id == asset_id)
    result = await session.execute(stmt)
    row = result.fetchone()
    return row[0] if row else ""


@router.get("/tickers/search", response_model=TickerSearchResponse)
async def ticker_search(
    query: str = Query(..., min_length=2, description="Search query (name or symbol)"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results to return"),
) -> TickerSearchResponse:
    """Search for ticker symbols by name or symbol using Polygon reference API."""
    return await search_tickers(query=query, limit=limit)


@router.get("/status", response_model=IngestionStatusResponse)
async def ingestion_status() -> IngestionStatusResponse:
    """Return ingestion pipeline health and scheduled job status."""
    jobs = list_jobs()
    return IngestionStatusResponse(
        status="running",
        active_jobs=len(jobs),
        scheduled_jobs=jobs,
    )
