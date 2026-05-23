from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from features.ml import job_runner


@pytest.mark.asyncio
async def test_execute_ml_data_preview_job():
    session = AsyncMock()
    preview = {"decision_timeframe": "1d", "bar_counts": {"1d": 10}, "warnings": []}
    job_id = uuid4()

    with patch(
        "features.ml.job_runner.preview_ml_data_for_symbol",
        new=AsyncMock(return_value=preview),
    ) as mock_preview:
        result = await job_runner.execute_ml_job(
            session,
            "ml_data_preview",
            {"symbol": "AAPL", "params": {}, "timeframe": "1d"},
            job_id=job_id,
        )

    assert result == preview
    mock_preview.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_ml_training_export_job():
    session = AsyncMock()
    payload = {
        "filename": "AAPL_training.xlsx",
        "content_base64": "UEsDBA==",
        "row_count": 100,
        "scope": "all_labeled",
    }
    job_id = uuid4()

    with patch(
        "features.ml.job_runner.export_training_data_for_symbol",
        new=AsyncMock(return_value=payload),
    ) as mock_export:
        result = await job_runner.execute_ml_job(
            session,
            "ml_training_export",
            {
                "symbol": "AAPL",
                "params": {},
                "timeframe": "1d",
                "scope": "all_labeled",
            },
            job_id=job_id,
        )

    assert result == payload
    mock_export.assert_awaited_once()
