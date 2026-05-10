"""Core ingestion orchestration logic (separated from routes)."""
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import (
    bulk_insert_fundamentals,
    bulk_insert_ohlcv,
    get_latest_timestamp,
    upsert_asset,
)
from dtos.market_data_dto import IngestRequest, OHLCVRecord
from features.data_ingestion.providers import get_provider
from features.data_ingestion.sanitizer import run_sanitization_pipeline
from utils.logging import get_logger
from utils.time_utils import timeframe_to_timedelta, utcnow

logger = get_logger(__name__)


async def ingest_ohlcv_for_symbol(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    provider_name: str,
    start: Optional[datetime],
    end: Optional[datetime],
) -> dict:
    """Fetch, sanitize, and persist OHLCV for one symbol+timeframe."""
    symbol = symbol.upper()
    provider = get_provider(provider_name)

    asset_id = await upsert_asset(session, symbol, asset_type="stock")

    if start is None:
        latest = await get_latest_timestamp(session, asset_id, timeframe)
        start = (
            latest + timeframe_to_timedelta(timeframe)
            if latest
            else datetime(1970, 1, 1, tzinfo=timezone.utc)
        )
    if end is None:
        end = utcnow()

    records = await provider.fetch_ohlcv(symbol, timeframe, start, end, asset_id=asset_id)

    if not records:
        logger.info("no_records_fetched", symbol=symbol, timeframe=timeframe)
        return {"symbol": symbol, "timeframe": timeframe, "inserted": 0}

    df = _records_to_df(records)
    df = run_sanitization_pipeline(df, timeframe)
    clean_records = _df_to_records(df, asset_id, timeframe, provider_name)

    inserted = await bulk_insert_ohlcv(session, clean_records)
    logger.info("ingest_complete", symbol=symbol, timeframe=timeframe, inserted=inserted)
    return {"symbol": symbol, "timeframe": timeframe, "inserted": inserted}


async def ingest_fundamentals_for_symbol(
    session: AsyncSession,
    symbol: str,
    provider_name: str,
) -> dict:
    """Fetch and persist fundamentals for one symbol."""
    symbol = symbol.upper()
    provider = get_provider(provider_name)
    asset_id = await upsert_asset(session, symbol, asset_type="stock")
    records = await provider.fetch_fundamentals(symbol, asset_id=asset_id)
    inserted = await bulk_insert_fundamentals(session, records)
    logger.info("fundamentals_ingest_complete", symbol=symbol, inserted=inserted)
    return {"symbol": symbol, "inserted": inserted}


async def run_ingest_job(session: AsyncSession, request: IngestRequest) -> list[dict]:
    """Orchestrate multi-symbol, multi-timeframe ingestion."""
    results = []
    for symbol in request.symbols:
        for timeframe in request.timeframes:
            try:
                result = await ingest_ohlcv_for_symbol(
                    session, symbol, timeframe,
                    request.provider,
                    request.start_date,
                    request.end_date,
                )
                results.append({**result, "status": "ok"})
            except Exception as exc:
                logger.error("ingest_failed", symbol=symbol, timeframe=timeframe, error=str(exc))
                results.append({"symbol": symbol, "timeframe": timeframe, "status": "error", "error": str(exc)})
    return results


def _records_to_df(records: list[OHLCVRecord]) -> pd.DataFrame:
    return pd.DataFrame([r.model_dump() for r in records])


def _df_to_records(df: pd.DataFrame, asset_id: int, timeframe: str, source: str) -> list[OHLCVRecord]:
    records = []
    for _, row in df.iterrows():
        records.append(OHLCVRecord(
            time=row["time"],
            asset_id=asset_id,
            timeframe=timeframe,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
            vwap=row.get("vwap"),
            source=source,
        ))
    return records
