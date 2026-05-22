from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dal import instrument_dal, ohlcv_dal
from db import get_db
from dtos.market_data_dto import (
    OHLCVBarDTO,
    OHLCVQueryResponse,
    PerformancePeriodDTO,
    PerformanceResponseDTO,
    StockKpiItemDTO,
    StockKpisResponseDTO,
)
from features.market_data.ohlcv_resample import SUPPORTED_TIMEFRAMES, is_tail_timeframe
from features.market_data.performance_service import load_performance
from features.market_data.stock_kpis import load_stock_kpis

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
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported timeframe: {timeframe}. Supported: {sorted(SUPPORTED_TIMEFRAMES)}",
        )

    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument not found: {symbol.upper()}")

    effective_end = end or datetime.now(timezone.utc)
    if start is not None and start > effective_end:
        raise HTTPException(status_code=400, detail="start must be before or equal to end")

    fetch_tail = is_tail_timeframe(timeframe)
    effective_start = start
    if effective_start is None and not fetch_tail:
        effective_start = ohlcv_dal.default_start_for_timeframe(timeframe)

    bars, resolved_source = await ohlcv_dal.get_bars_with_resample(
        session,
        instrument["id"],
        timeframe,
        source=source,
        start=effective_start,
        end=effective_end,
        limit=limit,
        fetch_tail=fetch_tail,
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


@router.get("/performance/{symbol}", response_model=PerformanceResponseDTO)
async def get_performance(
    symbol: str,
    session: AsyncSession = Depends(get_db),
) -> PerformanceResponseDTO:
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument not found: {symbol.upper()}")

    periods, as_of = await load_performance(session, instrument["id"])
    periods_dto = [
        PerformancePeriodDTO(
            period=row["period"],
            change_pct=row.get("total_return_pct"),
            price_change_pct=row.get("price_change_pct"),
            dividend_return_pct=row.get("dividend_return_pct"),
            total_return_pct=row.get("total_return_pct"),
            example_investment=row.get("example_investment", 100),
            example_outcome=row.get("example_outcome"),
            example_dividend_income=row.get("example_dividend_income"),
        )
        for row in periods
    ]
    return PerformanceResponseDTO(
        symbol=instrument["symbol"],
        currency=instrument.get("currency") or "USD",
        as_of=as_of,
        periods=periods_dto,
    )


@router.get("/kpis/{symbol}", response_model=StockKpisResponseDTO)
async def get_stock_kpis(
    symbol: str,
    session: AsyncSession = Depends(get_db),
) -> StockKpisResponseDTO:
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument not found: {symbol.upper()}")

    price, as_of, kpis = await load_stock_kpis(
        session,
        instrument["id"],
        symbol=instrument["symbol"],
        tiingo_ticker=instrument.get("tiingo_ticker"),
    )
    return StockKpisResponseDTO(
        symbol=instrument["symbol"],
        as_of=as_of,
        price=price,
        kpis=[
            StockKpiItemDTO(
                key=k.key,
                label=k.label,
                value=k.value,
                format=k.format,
            )
            for k in kpis
        ],
    )
