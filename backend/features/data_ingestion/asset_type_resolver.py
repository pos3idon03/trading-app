"""Resolve asset_type for ingestion (DB value vs yfinance-style crypto tickers)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_asset_type_by_symbol
from features.execution.symbol_resolver import _looks_like_yfinance_crypto_pair


async def resolve_asset_type(session: AsyncSession, symbol: str) -> str:
    """Return asset_type for a symbol during ingestion.

    Crypto-shaped tickers (e.g. BTC-USD) are always treated as crypto so a prior
    mis-ingest as stock does not route Tiingo to the IEX endpoint.
    """
    sym = symbol.upper()
    if _looks_like_yfinance_crypto_pair(sym):
        return "crypto"
    stored = await get_asset_type_by_symbol(session, sym)
    return stored or "stock"
