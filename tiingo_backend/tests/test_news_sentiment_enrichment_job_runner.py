from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from features.ingestion.job_runner import _dispatch


@pytest.mark.asyncio
async def test_dispatch_news_sentiment_enrichment_job():
    session = AsyncMock()
    job_id = uuid4()
    with patch(
        "features.ingestion.job_runner.run_news_sentiment_enrichment",
        new=AsyncMock(return_value={"enriched": 1}),
    ) as mock_run:
        result = await _dispatch(session, "news_sentiment_enrichment", {"batch_size": 5}, job_id)
    assert result["enriched"] == 1
    mock_run.assert_awaited_once()
