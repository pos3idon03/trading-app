from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from dal import job_dal
from utils.exceptions import JobCancelledError


@pytest.mark.asyncio
async def test_finish_job_applies_json_safe(monkeypatch):
    job_id = uuid4()
    evaluation_id = uuid4()
    bar_time = datetime(2026, 5, 28, 15, 0, tzinfo=timezone.utc)
    raw_result = {
        "deployment_id": job_id,
        "evaluation": {
            "id": evaluation_id,
            "bar_time": bar_time,
        },
    }
    safe_result = {"deployment_id": str(job_id), "evaluation": {"id": str(evaluation_id)}}
    json_safe = MagicMock(return_value=safe_result)
    monkeypatch.setattr(job_dal, "json_safe", json_safe)
    session = AsyncMock()

    await job_dal.finish_job(session, job_id, "completed", result=raw_result)

    json_safe.assert_called_once_with(raw_result)
    session.execute.assert_awaited_once()
    values = session.execute.await_args.args[0].compile().params
    stored_result = next(value for key, value in values.items() if key.startswith("result"))
    assert stored_result == safe_result


@pytest.mark.asyncio
async def test_ensure_job_active_raises_when_cancelled():
    job_id = uuid4()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: "cancelled"))

    with pytest.raises(JobCancelledError):
        await job_dal.ensure_job_active(session, job_id)


@pytest.mark.asyncio
async def test_update_job_progress_raises_when_cancelled():
    job_id = uuid4()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: "cancelled"))

    with pytest.raises(JobCancelledError):
        await job_dal.update_job_progress(session, job_id, 50)
