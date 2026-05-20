"""Core ingestion orchestration logic (separated from routes)."""
from datetime import datetime, timedelta, timezone
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
from features.data_ingestion.asset_type_resolver import resolve_asset_type
from features.data_ingestion.providers import get_provider
from features.data_ingestion.sanitizer import run_sanitization_pipeline
from utils.logging import get_logger
from utils.time_utils import timeframe_to_timedelta, utcnow

logger = get_logger(__name__)

_TIINGO_5M_LOOKBACK_DAYS = 90


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
    asset_type = await resolve_asset_type(session, symbol)
    asset_id = await upsert_asset(session, symbol, asset_type=asset_type)

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


async def ingest_tiingo_5m_for_symbol(
    session: AsyncSession,
    symbol: str,
    asset_type: str | None = None,
) -> dict:
    """Fetch and persist the last 90 days of 5m Tiingo bars for one symbol (incremental)."""
    symbol = symbol.upper()
    resolved_type = asset_type or await resolve_asset_type(session, symbol)
    provider = get_provider("tiingo")
    asset_id = await upsert_asset(session, symbol, asset_type=resolved_type)

    latest = await get_latest_timestamp(session, asset_id, "5m")
    if latest:
        start = latest + timeframe_to_timedelta("5m")
    else:
        start = utcnow() - timedelta(days=_TIINGO_5M_LOOKBACK_DAYS)

    end = utcnow()

    if start >= end:
        logger.info("tiingo_5m_already_up_to_date", symbol=symbol)
        return {"symbol": symbol, "timeframe": "5m", "inserted": 0}

    records = await provider.fetch_ohlcv(
        symbol, "5m", start, end, asset_id=asset_id, asset_type=resolved_type
    )

    if not records:
        return {"symbol": symbol, "timeframe": "5m", "inserted": 0}

    df = _records_to_df(records)
    df = run_sanitization_pipeline(df, "5m")
    clean_records = _df_to_records(df, asset_id, "5m", "tiingo")

    inserted = await bulk_insert_ohlcv(session, clean_records)
    logger.info("tiingo_5m_ingest_complete", symbol=symbol, inserted=inserted)
    return {"symbol": symbol, "timeframe": "5m", "inserted": inserted}


async def run_ingest_job(session: AsyncSession, request: IngestRequest) -> list[dict]:
    """Orchestrate multi-symbol, multi-timeframe ingestion."""
    results = []
    needs_5m_backfill = "1d" in request.timeframes and request.provider == "yfinance"

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

        if needs_5m_backfill:
            try:
                asset_type = await resolve_asset_type(session, symbol)
                result = await ingest_tiingo_5m_for_symbol(
                    session, symbol, asset_type=asset_type
                )
                results.append({**result, "provider": "tiingo", "status": "ok"})
            except Exception as exc:
                logger.error("tiingo_5m_backfill_failed", symbol=symbol, error=str(exc))
                results.append({"symbol": symbol, "timeframe": "5m", "provider": "tiingo", "status": "error", "error": str(exc)})

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
