from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from dal import macro_dal
from models.macro import MacroObservation


def _make_obs(obs_date: date, value: float = 1.0) -> MagicMock:
    row = MagicMock(spec=MacroObservation)
    row.obs_date = obs_date
    row.value = value
    return row


@pytest.mark.asyncio
async def test_get_latest_obs_date():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = date(2024, 5, 1)
    session.execute.return_value = result_mock

    latest = await macro_dal.get_latest_obs_date(session, "DGS10")

    assert latest == date(2024, 5, 1)


@pytest.mark.asyncio
async def test_get_observations_without_limit():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [
        _make_obs(date(2024, 1, 1)),
        _make_obs(date(2024, 2, 1), 2.0),
    ]
    session.execute.return_value = result_mock

    rows = await macro_dal.get_observations(session, "DGS10", limit=None, order="asc")

    assert len(rows) == 2
    assert rows[1]["value"] == 2.0


@pytest.mark.asyncio
async def test_bulk_insert_observations_batches_large_payloads():
    session = AsyncMock()
    session.execute.return_value = MagicMock(rowcount=5000)

    rows = [
        {"series_id": "T10Y2Y", "obs_date": date(2020, 1, 1), "value": 1.0}
        for _ in range(6000)
    ]
    inserted = await macro_dal.bulk_insert_observations(session, rows)

    assert inserted == 10000
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_get_observations_with_limit():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [_make_obs(date(2024, 1, 1))]
    session.execute.return_value = result_mock

    rows = await macro_dal.get_observations(session, "DGS10", limit=1, order="desc")

    assert len(rows) == 1
