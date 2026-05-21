from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from dal import fundamentals_dal


@pytest.mark.asyncio
async def test_bulk_insert_stamps_stored_at():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.rowcount = 1
    session.execute.return_value = result_mock

    rows = [
        {
            "time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "instrument_id": 1,
            "metric_name": "rev",
            "value": 1.0,
            "source": "tiingo",
        }
    ]
    stamped = fundamentals_dal._stamp_stored_at(rows)
    assert "stored_at" in stamped[0]

    count = await fundamentals_dal.bulk_insert_fundamentals(session, rows)
    assert count == 1
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_list_fundamentals_coverage_returns_rows():
    t1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
    t3 = datetime(2025, 5, 21, 12, 0, tzinfo=timezone.utc)

    row = MagicMock()
    row._mapping = {
        "symbol": "AAPL",
        "name": "Apple Inc",
        "metric_count": 42,
        "first_report_date": t1,
        "latest_report_date": t2,
        "last_ingested_at": t3,
    }
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.__iter__ = lambda self: iter([row])
    session.execute.return_value = result_mock

    rows = await fundamentals_dal.list_fundamentals_coverage(session)

    assert len(rows) == 1
    assert rows[0]["symbol"] == "AAPL"
    assert rows[0]["metric_count"] == 42
    assert rows[0]["last_ingested_at"] == t3


@pytest.mark.asyncio
async def test_bulk_insert_empty_returns_zero():
    session = AsyncMock()
    count = await fundamentals_dal.bulk_insert_fundamentals(session, [])
    assert count == 0
    session.execute.assert_not_called()
