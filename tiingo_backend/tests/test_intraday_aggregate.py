from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from dtos.market_data_dto import OHLCVRecord
from features.ingestion.intraday_aggregate import persist_derived_intraday_bars


@pytest.mark.asyncio
async def test_persist_derived_4h_from_hourly():
    start = datetime(2024, 1, 1, 9, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, 17, tzinfo=timezone.utc)
    hourly = [
        {
            "time": datetime(2024, 1, 1, 9, tzinfo=timezone.utc),
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100.5,
            "volume": 1000,
            "source": "tiingo_iex",
        },
        {
            "time": datetime(2024, 1, 1, 10, tzinfo=timezone.utc),
            "open": 100.5,
            "high": 102,
            "low": 100,
            "close": 101,
            "volume": 800,
            "source": "tiingo_iex",
        },
        {
            "time": datetime(2024, 1, 1, 13, tzinfo=timezone.utc),
            "open": 101,
            "high": 103,
            "low": 100.5,
            "close": 102,
            "volume": 900,
            "source": "tiingo_iex",
        },
    ]
    session = AsyncMock()

    with patch(
        "features.ingestion.intraday_aggregate.ohlcv_dal.get_bars",
        new=AsyncMock(return_value=(hourly, "tiingo_iex")),
    ) as mock_get, patch(
        "features.ingestion.intraday_aggregate.ohlcv_dal.bulk_insert_ohlcv",
        new=AsyncMock(return_value=1),
    ) as mock_insert:
        inserted = await persist_derived_intraday_bars(
            session,
            1,
            source_timeframe="1h",
            source="tiingo_iex",
            start=start,
            end=end,
        )

    assert inserted == 1
    mock_get.assert_awaited_once()
    records = mock_insert.await_args.args[1]
    assert all(isinstance(r, OHLCVRecord) for r in records)
    assert records[0].timeframe == "4h"


@pytest.mark.asyncio
async def test_persist_derived_returns_zero_when_no_hourly():
    session = AsyncMock()
    with patch(
        "features.ingestion.intraday_aggregate.ohlcv_dal.get_bars",
        new=AsyncMock(return_value=([], None)),
    ):
        inserted = await persist_derived_intraday_bars(
            session,
            1,
            source_timeframe="1h",
            source="tiingo_iex",
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
    assert inserted == 0
