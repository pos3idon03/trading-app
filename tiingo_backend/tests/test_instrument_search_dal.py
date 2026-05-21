from unittest.mock import AsyncMock, MagicMock

import pytest

from dal.instrument_dal import search_instruments
from models.instrument import Instrument


def _make_row(symbol: str, name: str, asset_type: str = "stock") -> MagicMock:
    row = MagicMock(spec=Instrument)
    row.id = 1
    row.symbol = symbol
    row.tiingo_ticker = symbol
    row.name = name
    row.asset_type = asset_type
    row.exchange = None
    row.currency = "USD"
    row.is_active = True
    row.metadata_ = None
    return row


@pytest.mark.asyncio
async def test_search_instruments_by_symbol():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [_make_row("AAPL", "Apple Inc")]
    session.execute.return_value = result_mock

    results = await search_instruments(session, "AAP", asset_types=["stock"], limit=10)

    assert len(results) == 1
    assert results[0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_search_instruments_filters_asset_type():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute.return_value = result_mock

    await search_instruments(session, "BTC", asset_types=["crypto"], limit=5)

    stmt = session.execute.call_args[0][0]
    compiled = str(stmt)
    assert "asset_type" in compiled
