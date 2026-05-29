from unittest.mock import AsyncMock, patch

import pytest

from features.fred.macro_orchestrator import macro_job_has_observation_changes
from features.ingestion.job_runner import _maybe_enqueue_macro_brief


def test_macro_job_has_observation_changes_true():
    result = {
        "UNRATE": {"inserted": 2, "status": "ok"},
        "CPIAUCSL": {"inserted": 0, "status": "ok"},
    }
    assert macro_job_has_observation_changes(result) is True


def test_macro_job_has_observation_changes_false():
    result = {
        "UNRATE": {"inserted": 0, "status": "ok"},
        "CPIAUCSL": {"inserted": 0, "status": "ok"},
    }
    assert macro_job_has_observation_changes(result) is False


@pytest.mark.asyncio
async def test_maybe_enqueue_macro_brief_after_refresh_with_insertions():
    result = {"UNRATE": {"inserted": 1, "status": "ok"}}

    with patch(
        "features.ingestion.job_runner.AsyncSessionLocal",
    ) as session_factory, patch(
        "features.worker.tasks.create_and_enqueue_job",
        new=AsyncMock(),
    ) as enqueue_mock:
        session = AsyncMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        await _maybe_enqueue_macro_brief("macro_refresh", result, "completed")

    enqueue_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_maybe_enqueue_macro_brief_bootstraps_when_no_stored_brief():
    result = {"UNRATE": {"inserted": 0, "status": "ok"}}

    with patch(
        "features.ingestion.job_runner.AsyncSessionLocal",
    ) as session_factory, patch(
        "features.ingestion.job_runner._should_enqueue_macro_brief",
        new=AsyncMock(return_value=True),
    ), patch(
        "features.worker.tasks.create_and_enqueue_job",
        new=AsyncMock(),
    ) as enqueue_mock:
        session = AsyncMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        await _maybe_enqueue_macro_brief("macro_refresh", result, "completed")

    enqueue_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_maybe_enqueue_macro_brief_skips_without_trigger():
    result = {"UNRATE": {"inserted": 0, "status": "ok"}}

    with patch(
        "features.ingestion.job_runner.AsyncSessionLocal",
    ) as session_factory, patch(
        "features.ingestion.job_runner._should_enqueue_macro_brief",
        new=AsyncMock(return_value=False),
    ), patch(
        "features.worker.tasks.create_and_enqueue_job",
        new=AsyncMock(),
    ) as enqueue_mock:
        session = AsyncMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        await _maybe_enqueue_macro_brief("macro_refresh", result, "completed")

    enqueue_mock.assert_not_called()


@pytest.mark.asyncio
async def test_maybe_enqueue_macro_brief_runs_on_partial_with_insertions():
    result = {"UNRATE": {"inserted": 1, "status": "ok"}}

    with patch(
        "features.ingestion.job_runner.AsyncSessionLocal",
    ) as session_factory, patch(
        "features.worker.tasks.create_and_enqueue_job",
        new=AsyncMock(),
    ) as enqueue_mock:
        session = AsyncMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        await _maybe_enqueue_macro_brief("macro_backfill", result, "partial")

    enqueue_mock.assert_awaited_once()
