"""Unit tests for the APScheduler nightly ingestion job."""
from unittest.mock import AsyncMock, patch

import pytest
from apscheduler.triggers.cron import CronTrigger

from features.data_ingestion.scheduler import (
    _nightly_full_ingest,
    get_scheduler,
    register_default_jobs,
)


class TestRegisterDefaultJobs:
    """Verify that the nightly job is registered with correct settings."""

    def test_nightly_job_registered(self):
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        scheduler = AsyncIOScheduler(timezone="UTC")
        register_default_jobs(scheduler)

        job = scheduler.get_job("ingest_nightly_all_assets")
        assert job is not None
        assert job.name == "Nightly full price ingestion (all DB assets)"

    def test_nightly_job_cron_trigger_midnight(self):
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        scheduler = AsyncIOScheduler(timezone="UTC")
        register_default_jobs(scheduler)

        job = scheduler.get_job("ingest_nightly_all_assets")
        trigger = job.trigger
        assert isinstance(trigger, CronTrigger)
        # Verify hour=0, minute=0 by inspecting trigger fields
        hour_field = str(trigger.fields[trigger.FIELD_NAMES.index("hour")])
        minute_field = str(trigger.fields[trigger.FIELD_NAMES.index("minute")])
        assert hour_field == "0"
        assert minute_field == "0"


class TestNightlyFullIngest:
    """Verify the nightly job fetches all DB assets and runs ingestion."""

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.run_ingest_job", new_callable=AsyncMock)
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_ingests_all_active_assets(self, mock_session_local, mock_run_ingest):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        fake_assets = [
            {"id": 1, "symbol": "AAPL", "is_active": True},
            {"id": 2, "symbol": "MSFT", "is_active": True},
            {"id": 3, "symbol": "TSLA", "is_active": False},
        ]

        with patch(
            "dal.market_data_dal.list_assets",
            new_callable=AsyncMock,
            return_value=fake_assets,
        ):
            await _nightly_full_ingest()

        mock_run_ingest.assert_called_once()
        call_args = mock_run_ingest.call_args
        request = call_args[0][1]
        assert set(request.symbols) == {"AAPL", "MSFT"}
        assert request.timeframes == ["1d"]
        assert request.provider == "yfinance"

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.run_ingest_job", new_callable=AsyncMock)
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_skips_when_no_active_assets(self, mock_session_local, mock_run_ingest):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "dal.market_data_dal.list_assets",
            new_callable=AsyncMock,
            return_value=[],
        ):
            await _nightly_full_ingest()

        mock_run_ingest.assert_not_called()

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.run_ingest_job", new_callable=AsyncMock)
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_rollback_on_error(self, mock_session_local, mock_run_ingest):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_run_ingest.side_effect = RuntimeError("provider timeout")

        fake_assets = [{"id": 1, "symbol": "SPY", "is_active": True}]

        with patch(
            "dal.market_data_dal.list_assets",
            new_callable=AsyncMock,
            return_value=fake_assets,
        ):
            await _nightly_full_ingest()

        mock_session.rollback.assert_called_once()
