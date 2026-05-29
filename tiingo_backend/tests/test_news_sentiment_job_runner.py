from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from features.ingestion.job_runner import _dispatch


@pytest.mark.asyncio
async def test_dispatch_news_sentiment_job():
    session = AsyncMock()
    job_id = uuid4()
    with patch("features.ingestion.job_runner.run_news_sentiment", new=AsyncMock(return_value={"scored": 2})) as mock_run:
        result = await _dispatch(
            session,
            "news_sentiment",
            {"batch_size": 10, "backfill": False},
            job_id,
        )
    assert result["scored"] == 2
    mock_run.assert_awaited_once()
