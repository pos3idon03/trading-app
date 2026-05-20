"""Tests for MC backtest optimize job DAL."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from dal.mc_backtest_optimize_job_dal import (
    create_job,
    mark_done,
    mark_error,
    mark_running,
    update_progress,
)


class TestMcBacktestOptimizeJobDal:
    @pytest.mark.asyncio
    async def test_create_job_returns_id(self):
        session = AsyncMock()
        session.flush = AsyncMock()

        job_id = await create_job(
            session,
            asset_id=1,
            symbol="AAPL",
            request_dict={"optimize_metric": "sharpe_ratio", "n_splits": 5},
        )

        assert job_id is not None
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_running_sets_total_steps(self):
        session = AsyncMock()
        job = MagicMock()
        session.get = AsyncMock(return_value=job)

        await mark_running(session, job_id=7, total_steps=481)

        assert job.status == "running"
        assert job.total_steps == 481
        assert job.completed_steps == 0
        assert job.progress_pct == 0.0

    @pytest.mark.asyncio
    async def test_update_progress_sets_pct(self):
        session = AsyncMock()
        job = MagicMock()
        session.get = AsyncMock(return_value=job)

        await update_progress(session, job_id=7, completed=240, total=480, message="Fold 3/5")

        assert job.completed_steps == 240
        assert job.total_steps == 480
        assert job.progress_pct == pytest.approx(50.0)
        assert job.progress_message == "Fold 3/5"

    @pytest.mark.asyncio
    async def test_mark_done_persists_result(self):
        session = AsyncMock()
        job = MagicMock(total_steps=10)
        session.get = AsyncMock(return_value=job)
        result = {"best_params": {"buy_threshold": 0.52}, "status": "done"}

        await mark_done(session, job_id=3, result_dict=result, duration_ms=1200)

        assert job.status == "done"
        assert job.result == result
        assert job.duration_ms == 1200
        assert job.progress_pct == 100.0
        assert job.completed_steps == 10

    @pytest.mark.asyncio
    async def test_mark_error_persists_message(self):
        session = AsyncMock()
        job = MagicMock()
        session.get = AsyncMock(return_value=job)

        await mark_error(session, job_id=3, error_message="No feasible combos", duration_ms=50)

        assert job.status == "error"
        assert job.error_message == "No feasible combos"
        assert job.progress_message == "Failed"
