"""Core logic for fetching and persisting financial fundamentals per symbol."""
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import bulk_insert_fundamentals, upsert_asset, upsert_company_profile
from features.data_ingestion.providers import get_provider
from utils.logging import get_logger

logger = get_logger(__name__)


async def ingest_financials_for_symbol(
    session: AsyncSession,
    symbol: str,
    provider_name: str = "yfinance",
) -> dict:
    """Fetch and persist fundamentals, statements, and company profile for one symbol."""
    symbol = symbol.upper()
    provider = get_provider(provider_name)
    asset_id = await upsert_asset(session, symbol, asset_type="stock")

    records = await _fetch_all_fundamental_records(provider, symbol, asset_id)
    inserted = await bulk_insert_fundamentals(session, records)

    profile_updated = await _fetch_and_store_profile(session, provider, symbol, asset_id)

    logger.info(
        "financials_ingest_complete",
        symbol=symbol,
        fundamentals_inserted=inserted,
        profile_updated=profile_updated,
    )
    return {
        "symbol": symbol,
        "fundamentals_inserted": inserted,
        "profile_updated": profile_updated,
    }


async def _fetch_all_fundamental_records(provider, symbol: str, asset_id: int) -> list:
    """Combine scalar fundamentals and financial statement records."""
    records = await provider.fetch_fundamentals(symbol, asset_id=asset_id)
    records.extend(await provider.fetch_financial_statements(symbol, asset_id=asset_id))
    return records


async def _fetch_and_store_profile(
    session: AsyncSession,
    provider,
    symbol: str,
    asset_id: int,
) -> bool:
    """Fetch company profile and persist it; returns True if data was saved."""
    profile_data = await provider.fetch_company_profile(symbol)
    if not profile_data or not any(v for v in profile_data.values() if v is not None):
        logger.info("no_profile_data", symbol=symbol)
        return False
    profile_data["source"] = provider.name
    await upsert_company_profile(session, asset_id, profile_data)
    return True
