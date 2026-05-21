from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from features.fred.macro_orchestrator import backfill_series, refresh_enabled


@pytest.mark.asyncio
async def test_backfill_uses_full_fetch():
    session = AsyncMock()
    obs = [{"series_id": "DGS10", "obs_date": date(2024, 1, 1), "value": 4.0}]

    with patch(
        "features.fred.macro_orchestrator.fred_client.fetch_all_observations",
        new=AsyncMock(return_value=obs),
    ) as mock_fetch, patch(
        "features.fred.macro_orchestrator.macro_dal.bulk_insert_observations",
        new=AsyncMock(return_value=1),
    ), patch(
        "features.fred.macro_orchestrator.macro_dal.set_series_enabled",
        new=AsyncMock(),
    ):
        result = await backfill_series(session, ["DGS10"])

    mock_fetch.assert_awaited_once_with("DGS10")
    assert result["DGS10"]["status"] == "ok"
    assert result["DGS10"]["inserted"] == 1


@pytest.mark.asyncio
async def test_refresh_uses_incremental_when_latest_exists():
    session = AsyncMock()
    obs = [{"series_id": "DGS10", "obs_date": date(2024, 6, 1), "value": 4.5}]

    with patch(
        "features.fred.macro_orchestrator.macro_dal.get_enabled_series_ids",
        new=AsyncMock(return_value=["DGS10"]),
    ), patch(
        "features.fred.macro_orchestrator.macro_dal.get_latest_obs_date",
        new=AsyncMock(return_value=date(2024, 5, 31)),
    ), patch(
        "features.fred.macro_orchestrator.fred_client.fetch_observations_since",
        new=AsyncMock(return_value=obs),
    ) as mock_since, patch(
        "features.fred.macro_orchestrator.fred_client.fetch_all_observations",
        new=AsyncMock(),
    ) as mock_all, patch(
        "features.fred.macro_orchestrator.macro_dal.bulk_insert_observations",
        new=AsyncMock(return_value=1),
    ), patch(
        "features.fred.macro_orchestrator.macro_dal.set_series_enabled",
        new=AsyncMock(),
    ):
        result = await refresh_enabled(session)

    mock_since.assert_awaited_once_with("DGS10", date(2024, 6, 1))
    mock_all.assert_not_awaited()
    assert result["DGS10"]["status"] == "ok"


@pytest.mark.asyncio
async def test_refresh_full_fetch_when_no_latest():
    session = AsyncMock()

    with patch(
        "features.fred.macro_orchestrator.macro_dal.get_enabled_series_ids",
        new=AsyncMock(return_value=["DGS10"]),
    ), patch(
        "features.fred.macro_orchestrator.macro_dal.get_latest_obs_date",
        new=AsyncMock(return_value=None),
    ), patch(
        "features.fred.macro_orchestrator.fred_client.fetch_all_observations",
        new=AsyncMock(return_value=[]),
    ) as mock_all, patch(
        "features.fred.macro_orchestrator.macro_dal.bulk_insert_observations",
        new=AsyncMock(return_value=0),
    ), patch(
        "features.fred.macro_orchestrator.macro_dal.set_series_enabled",
        new=AsyncMock(),
    ):
        result = await refresh_enabled(session)

    mock_all.assert_awaited_once_with("DGS10")
    assert result["DGS10"]["status"] == "ok"
