"""Tests for instrument DAL upsert (metadata column name must not break SQLAlchemy)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dal.instrument_dal import delete_instrument, upsert_instrument
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


@pytest.mark.asyncio
async def test_upsert_normalizes_crypto_symbol():
    session = AsyncMock()
    mapping = {
        "id": 2,
        "symbol": "BTC-USD",
        "tiingo_ticker": "btcusd",
        "name": "Bitcoin USD",
        "asset_type": "crypto",
        "exchange": None,
        "currency": "USD",
        "is_active": True,
        "metadata": None,
    }
    result_mock = MagicMock()
    result_mock.mappings.return_value.one.return_value = mapping
    session.execute = AsyncMock(return_value=result_mock)

    with patch("dal.instrument_dal.normalize_crypto_symbol", return_value="BTC-USD") as mock_norm:
        result = await upsert_instrument(
            session,
            {"symbol": "btcusd", "asset_type": "crypto", "tiingo_ticker": "btcusd"},
        )

    mock_norm.assert_called_once_with("btcusd")
    assert result["symbol"] == "BTC-USD"


@pytest.mark.asyncio
async def test_delete_instrument_returns_false_when_missing():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock

    deleted = await delete_instrument(session, "UNKNOWN")

    assert deleted is False
    session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_instrument_deletes_row_when_found():
    session = AsyncMock()
    mock_row = MagicMock(spec=Instrument)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_row
    session.execute.return_value = result_mock

    deleted = await delete_instrument(session, "aapl")

    assert deleted is True
    session.delete.assert_called_once_with(mock_row)
