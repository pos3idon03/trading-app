"""Tests for resolve_asset_type during ingestion."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.data_ingestion.asset_type_resolver import resolve_asset_type


@pytest.mark.asyncio
async def test_crypto_pair_always_crypto_even_if_db_says_stock():
    session = MagicMock()
    with patch(
        "features.data_ingestion.asset_type_resolver.get_asset_type_by_symbol",
        new=AsyncMock(return_value="stock"),
    ):
        assert await resolve_asset_type(session, "BTC-USD") == "crypto"


@pytest.mark.asyncio
async def test_hyphenated_equity_not_crypto():
    session = MagicMock()
    with patch(
        "features.data_ingestion.asset_type_resolver.get_asset_type_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        assert await resolve_asset_type(session, "BRK-B") == "stock"


@pytest.mark.asyncio
async def test_uses_stored_type_for_equity():
    session = MagicMock()
    with patch(
        "features.data_ingestion.asset_type_resolver.get_asset_type_by_symbol",
        new=AsyncMock(return_value="etf"),
    ):
        assert await resolve_asset_type(session, "SPY") == "etf"
