from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from features.ingestion import job_runner
from utils.exceptions import JobCancelledError


@pytest.mark.asyncio
async def test_execute_job_skips_when_already_cancelled():
    job_id = uuid4()

    with patch.object(
        job_runner,
        "_job_was_cancelled",
        new=AsyncMock(return_value=True),
    ), patch(
        "features.ingestion.job_runner.job_dal.start_job",
        new=AsyncMock(),
    ) as start_job:
        await job_runner.execute_job(job_id, "ml_data_preview", {})

    start_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_job_handles_cancellation_during_dispatch():
    job_id = uuid4()

    with patch.object(
        job_runner,
        "_job_was_cancelled",
        side_effect=[False, False],
    ), patch(
        "features.ingestion.job_runner.job_dal.start_job",
        new=AsyncMock(),
    ), patch(
        "features.ingestion.job_runner._dispatch",
        new=AsyncMock(side_effect=JobCancelledError()),
    ), patch(
        "features.ingestion.job_runner.job_dal.finish_job",
        new=AsyncMock(),
    ) as finish_job:
        await job_runner.execute_job(job_id, "ml_data_preview", {})

    finish_job.assert_not_awaited()
