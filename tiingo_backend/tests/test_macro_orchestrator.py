from datetime import date
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

from uuid import uuid4

from features.fred.macro_orchestrator import (
    backfill_alfred_releases,
    backfill_series,
    has_partial_macro_results,
    refresh_enabled,
)


@contextmanager
def _patch_release_date_ingest(*, fallback_updated: int = 0):
    with patch(
        "features.fred.macro_orchestrator.alfred_client.fetch_initial_release_observations",
        new=AsyncMock(return_value=[]),
    ), patch(
        "features.fred.macro_orchestrator.macro_dal.backfill_same_day_release_dates",
        new=AsyncMock(return_value=fallback_updated),
    ), patch(
        "features.fred.macro_orchestrator.macro_dal.get_release_date_coverage",
        new=AsyncMock(return_value={"total": 1, "with_release_date": 1, "pct": 100.0}),
    ):
        yield


@pytest.mark.asyncio
async def test_backfill_uses_full_fetch():
    session = AsyncMock()
    obs = [{"series_id": "DGS10", "obs_date": date(2024, 1, 1), "value": 4.0}]

    with _patch_release_date_ingest(), patch(
        "features.fred.macro_orchestrator.seed_catalog",
        new=AsyncMock(return_value=1),
    ), patch(
        "features.fred.macro_orchestrator.fred_client.fetch_all_observations",
        new=AsyncMock(return_value=obs),
    ) as mock_fetch, patch(
        "features.fred.macro_orchestrator.macro_dal.bulk_insert_observations",
        new=AsyncMock(return_value=1),
    ), patch(
        "features.fred.macro_orchestrator.macro_dal.set_series_enabled",
        new=AsyncMock(),
    ):
        result = await backfill_series(session, ["DGS10"], job_id=None)

    mock_fetch.assert_awaited_once_with("DGS10")
    assert result["DGS10"]["status"] == "ok"
    assert result["DGS10"]["inserted"] == 1


@pytest.mark.asyncio
async def test_refresh_uses_incremental_when_latest_exists():
    session = AsyncMock()
    obs = [{"series_id": "DGS10", "obs_date": date(2024, 6, 1), "value": 4.5}]

    with _patch_release_date_ingest(), patch(
        "features.fred.macro_orchestrator.seed_catalog",
        new=AsyncMock(return_value=1),
    ), patch(
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


def test_has_partial_macro_results():
    assert has_partial_macro_results({"DGS10": {"status": "error", "error": "x"}})
    assert not has_partial_macro_results({"DGS10": {"status": "ok", "inserted": 1}})


@pytest.mark.asyncio
async def test_backfill_updates_progress():
    session = AsyncMock()
    job_id = uuid4()

    with patch(
        "features.fred.macro_orchestrator.seed_catalog",
        new=AsyncMock(return_value=1),
    ), patch(
        "features.fred.macro_orchestrator._ingest_series",
        new=AsyncMock(return_value=1),
    ), patch(
        "features.fred.macro_orchestrator.job_dal.update_job_progress",
        new=AsyncMock(),
    ) as mock_progress:
        await backfill_series(session, ["DGS10", "GDP"], job_id=job_id)

    assert mock_progress.await_count == 2


@pytest.mark.asyncio
async def test_refresh_full_fetch_when_no_latest():
    session = AsyncMock()

    with _patch_release_date_ingest(), patch(
        "features.fred.macro_orchestrator.seed_catalog",
        new=AsyncMock(return_value=1),
    ), patch(
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


@pytest.mark.asyncio
async def test_alfred_backfill_applies_same_day_fallback_when_alfred_fails():
    session = AsyncMock()

    with patch(
        "features.fred.macro_orchestrator.seed_catalog",
        new=AsyncMock(return_value=1),
    ), patch(
        "features.fred.macro_orchestrator.alfred_client.fetch_initial_release_observations",
        new=AsyncMock(side_effect=RuntimeError("400 Bad Request")),
    ), patch(
        "features.fred.macro_orchestrator.macro_dal.backfill_same_day_release_dates",
        new=AsyncMock(return_value=100),
    ) as mock_fallback, patch(
        "features.fred.macro_orchestrator.macro_dal.get_release_date_coverage",
        new=AsyncMock(return_value={"total": 100, "with_release_date": 100, "pct": 100.0}),
    ):
        result = await backfill_alfred_releases(session, ["DFF"], job_id=None)

    mock_fallback.assert_awaited_once_with(session, "DFF")
    assert result["DFF"]["status"] == "ok"
    assert result["DFF"]["alfred_updated"] == 0
    assert result["DFF"]["fallback_updated"] == 100
    assert result["DFF"]["release_date_coverage_pct"] == 100.0


@pytest.mark.asyncio
async def test_alfred_backfill_skips_fallback_for_non_rate_series():
    session = AsyncMock()

    with patch(
        "features.fred.macro_orchestrator.seed_catalog",
        new=AsyncMock(return_value=1),
    ), patch(
        "features.fred.macro_orchestrator.alfred_client.fetch_initial_release_observations",
        new=AsyncMock(return_value=[]),
    ), patch(
        "features.fred.macro_orchestrator.macro_dal.backfill_same_day_release_dates",
        new=AsyncMock(return_value=0),
    ) as mock_fallback, patch(
        "features.fred.macro_orchestrator.macro_dal.get_release_date_coverage",
        new=AsyncMock(return_value={"total": 0, "with_release_date": 0, "pct": 0.0}),
    ):
        result = await backfill_alfred_releases(session, ["CPIAUCSL"], job_id=None)

    mock_fallback.assert_not_awaited()
    assert result["CPIAUCSL"]["fallback_updated"] == 0

