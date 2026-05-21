from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dal import fundamentals_dal, instrument_dal
from db import get_db

router = APIRouter(prefix="/ingestion/fundamentals", tags=["fundamentals"])


@router.get("/{symbol}")
async def get_fundamentals(symbol: str, session: AsyncSession = Depends(get_db)):
    inst = await instrument_dal.get_by_symbol(session, symbol)
    if not inst:
        raise HTTPException(404, "Instrument not found")
    rows = await fundamentals_dal.list_fundamentals_for_symbol(session, inst["id"])
    return {"symbol": symbol, "metrics": rows}
