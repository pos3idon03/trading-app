from unittest.mock import AsyncMock, patch

import pytest

from features.fred.macro_seed_schedule import (
    MACRO_SEED_CATALOG_JOB_TYPE,
    should_enqueue_macro_seed_catalog,
)


@pytest.mark.asyncio
async def test_should_enqueue_when_no_recent_or_active_jobs():
    session = AsyncMock()
    with patch(
        "features.fred.macro_seed_schedule.job_dal.has_active_or_recent_job",
        new_callable=AsyncMock,
        return_value=False,
    ) as has_recent:
        assert await should_enqueue_macro_seed_catalog(session) is True
        has_recent.assert_awaited_once_with(
            session,
            MACRO_SEED_CATALOG_JOB_TYPE,
            within_hours=24,
        )


@pytest.mark.asyncio
async def test_should_not_enqueue_when_recent_job_exists():
    session = AsyncMock()
    with patch(
        "features.fred.macro_seed_schedule.job_dal.has_active_or_recent_job",
        new_callable=AsyncMock,
        return_value=True,
    ):
        assert await should_enqueue_macro_seed_catalog(session) is False
