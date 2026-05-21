"""Tests for instrument DAL upsert (metadata column name must not break SQLAlchemy)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from dal.instrument_dal import upsert_instrument
from models.instrument import Instrument


@pytest.mark.asyncio
async def test_upsert_uses_metadata_orm_attr_not_reserved_key():
    session = AsyncMock()
    mock_row = MagicMock(spec=Instrument)
    mock_row.id = 1
    mock_row.symbol = "AAPL"
    mock_row.tiingo_ticker = "AAPL"
    mock_row.name = "Apple Inc"
    mock_row.asset_type = "stock"
    mock_row.exchange = None
    mock_row.currency = "USD"
    mock_row.is_active = True
    mock_row.metadata_ = None

    result_mock = MagicMock()
    result_mock.scalar_one.return_value = mock_row
    session.execute.return_value = result_mock

    captured_stmt = None

    async def capture_execute(stmt):
        nonlocal captured_stmt
        captured_stmt = stmt
        return result_mock

    session.execute = capture_execute

    await upsert_instrument(
        session,
        {
            "symbol": "AAPL",
            "name": "Apple Inc",
            "asset_type": "stock",
            "tiingo_ticker": "AAPL",
        },
    )

    assert captured_stmt is not None
    # Compiled statement must reference metadata column, not pass MetaData object
    compiled = str(captured_stmt)
    assert "metadata" in compiled.lower()
