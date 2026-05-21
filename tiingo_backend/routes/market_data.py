from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dal import instrument_dal, ohlcv_dal
from db import get_db
from dtos.market_data_dto import OHLCVBarDTO, OHLCVQueryResponse

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/ohlcv/{symbol}", response_model=OHLCVQueryResponse)
async def get_ohlcv_by_symbol(
    symbol: str,
    timeframe: str = Query(default="1d"),
    source: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=2000, ge=1, le=10000),
    session: AsyncSession = Depends(get_db),
) -> OHLCVQueryResponse:
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument not found: {symbol.upper()}")

    effective_start = start or ohlcv_dal.default_start_for_timeframe(timeframe)
    effective_end = end or datetime.now(timezone.utc)

    bars, resolved_source = await ohlcv_dal.get_bars(
        session,
        instrument["id"],
        timeframe,
        source=source,
        start=effective_start,
        end=effective_end,
        limit=limit,
    )
    if not bars:
        raise HTTPException(
            status_code=404,
            detail=f"No OHLCV data found for {symbol.upper()} ({timeframe})",
        )

    records = [OHLCVBarDTO(**bar) for bar in bars]
    return OHLCVQueryResponse(
        symbol=instrument["symbol"],
        instrument_id=instrument["id"],
        timeframe=timeframe,
        source=resolved_source or source or "",
        records=records,
        count=len(records),
    )
