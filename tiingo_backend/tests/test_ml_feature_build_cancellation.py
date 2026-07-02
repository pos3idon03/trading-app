from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from features.ml import feature_builder
from utils.exceptions import JobCancelledError


@pytest.mark.asyncio
async def test_build_ml_feature_matrix_checks_cancel_before_macro():
    session = AsyncMock()
    job_id = uuid4()
    bars = [{"close": 1.0, "time": "2024-01-01"}] * 300
    params = {
        "feature_mode": "prices_macro_fundamentals",
        "denoise_method": "none",
        "context_timeframes": [],
        "strategy_feature_ids": [],
    }

    with patch(
        "features.ml.job_checkpoints.run_cpu_bound_step",
        new=AsyncMock(
            side_effect=[
                (["px"], [[1.0]]),
                ([], [], [], [], [], []),
            ]
        ),
    ), patch(
        "features.ml.feature_builder._build_macro_features",
        new=AsyncMock(),
    ) as macro_mock, patch(
        "features.ml.job_checkpoints.checkpoint_ml_job",
        new=AsyncMock(side_effect=[None, None, JobCancelledError()]),
    ):
        with pytest.raises(JobCancelledError):
            await feature_builder.build_ml_feature_matrix(
                session,
                bars,
                params,
                instrument_id=1,
                symbol="AAPL",
                job_id=job_id,
                progress_start=35,
                progress_end=60,
            )

    macro_mock.assert_not_awaited()
