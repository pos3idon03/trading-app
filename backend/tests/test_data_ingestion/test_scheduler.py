"""Unit tests for the APScheduler ingestion and auto-trading scheduler."""
from unittest.mock import AsyncMock, patch

import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from features.data_ingestion.scheduler import (
    _auto_trading_evaluation_job,
    _daily_yfinance_ingest_job,
    _tiingo_5m_ingest_job,
    get_scheduler,
    register_default_jobs,
)


# ---------------------------------------------------------------------------
# Job registration
# ---------------------------------------------------------------------------

class TestRegisterDefaultJobs:
    """Verify that the 3 expected jobs are registered with correct settings."""

    def _make_scheduler(self):
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        return AsyncIOScheduler(timezone="UTC")

    def test_exactly_three_jobs_registered(self):
        scheduler = self._make_scheduler()
        register_default_jobs(scheduler)
        assert len(scheduler.get_jobs()) == 3

    def test_removed_jobs_not_present(self):
        scheduler = self._make_scheduler()
        register_default_jobs(scheduler)
        assert scheduler.get_job("ingest_1h") is None
        assert scheduler.get_job("price_streaming_ingest") is None
        assert scheduler.get_job("ingest_nightly_all_assets") is None

    def test_tiingo_5m_ingest_registered(self):
        scheduler = self._make_scheduler()
        register_default_jobs(scheduler)
        job = scheduler.get_job("tiingo_5m_ingest")
        assert job is not None
        assert "Tiingo" in job.name

    def test_tiingo_5m_ingest_cron_trigger_noon_athens(self):
        scheduler = self._make_scheduler()
        register_default_jobs(scheduler)
        job = scheduler.get_job("tiingo_5m_ingest")
        assert isinstance(job.trigger, CronTrigger)
        hour_field = str(job.trigger.fields[job.trigger.FIELD_NAMES.index("hour")])
        minute_field = str(job.trigger.fields[job.trigger.FIELD_NAMES.index("minute")])
        assert hour_field == "12"
        assert minute_field == "0"

    def test_ingest_daily_registered(self):
        scheduler = self._make_scheduler()
        register_default_jobs(scheduler)
        job = scheduler.get_job("ingest_daily")
        assert job is not None
        assert "Yahoo Finance" in job.name or "1d" in job.name or "Daily" in job.name

    def test_ingest_daily_cron_trigger_noon_athens(self):
        scheduler = self._make_scheduler()
        register_default_jobs(scheduler)
        job = scheduler.get_job("ingest_daily")
        assert isinstance(job.trigger, CronTrigger)
        hour_field = str(job.trigger.fields[job.trigger.FIELD_NAMES.index("hour")])
        minute_field = str(job.trigger.fields[job.trigger.FIELD_NAMES.index("minute")])
        assert hour_field == "12"
        assert minute_field == "0"

    def test_auto_trading_eval_registered(self):
        scheduler = self._make_scheduler()
        register_default_jobs(scheduler)
        job = scheduler.get_job("auto_trading_eval")
        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)


# ---------------------------------------------------------------------------
# _tiingo_5m_ingest_job
# ---------------------------------------------------------------------------

class TestTiingo5mIngestJob:
    """Verify _tiingo_5m_ingest_job fetches all active assets incrementally."""

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_ingests_active_assets_only(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        fake_assets = [
            {"id": 1, "symbol": "AAPL", "is_active": True},
            {"id": 2, "symbol": "MSFT", "is_active": True},
            {"id": 3, "symbol": "TSLA", "is_active": False},
        ]
        mock_ingest = AsyncMock(return_value={"symbol": "X", "timeframe": "5m", "inserted": 5})

        with (
            patch("dal.market_data_dal.list_assets", new_callable=AsyncMock, return_value=fake_assets),
            patch(
                "features.data_ingestion.ingest_service.ingest_tiingo_5m_for_symbol",
                mock_ingest,
            ),
        ):
            await _tiingo_5m_ingest_job()

        assert mock_ingest.call_count == 2
        called_symbols = {call[0][1] for call in mock_ingest.call_args_list}
        assert called_symbols == {"AAPL", "MSFT"}

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_passes_asset_type_for_crypto(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        fake_assets = [
            {"id": 1, "symbol": "BTC-USD", "is_active": True, "asset_type": "crypto"},
            {"id": 2, "symbol": "AAPL", "is_active": True, "asset_type": "stock"},
        ]
        mock_ingest = AsyncMock(return_value={"symbol": "X", "timeframe": "5m", "inserted": 1})

        with (
            patch("dal.market_data_dal.list_assets", new_callable=AsyncMock, return_value=fake_assets),
            patch(
                "features.data_ingestion.ingest_service.ingest_tiingo_5m_for_symbol",
                mock_ingest,
            ),
        ):
            await _tiingo_5m_ingest_job()

        assert mock_ingest.call_count == 2
        by_symbol = {c[0][1]: c[1]["asset_type"] for c in mock_ingest.call_args_list}
        assert by_symbol["BTC-USD"] == "crypto"
        assert by_symbol["AAPL"] == "stock"

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_skips_when_no_active_assets(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_ingest = AsyncMock()

        with (
            patch("dal.market_data_dal.list_assets", new_callable=AsyncMock, return_value=[]),
            patch(
                "features.data_ingestion.ingest_service.ingest_tiingo_5m_for_symbol",
                mock_ingest,
            ),
        ):
            await _tiingo_5m_ingest_job()

        mock_ingest.assert_not_called()

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_continues_on_symbol_error(self, mock_session_local):
        """A per-symbol error must not abort the whole job."""
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        fake_assets = [
            {"id": 1, "symbol": "AAPL", "is_active": True},
            {"id": 2, "symbol": "MSFT", "is_active": True},
        ]
        call_count = 0

        async def _flaky_ingest(session, symbol, asset_type="stock"):
            nonlocal call_count
            call_count += 1
            if symbol == "AAPL":
                raise RuntimeError("tiingo timeout")
            return {"symbol": symbol, "timeframe": "5m", "inserted": 3}

        with (
            patch("dal.market_data_dal.list_assets", new_callable=AsyncMock, return_value=fake_assets),
            patch(
                "features.data_ingestion.ingest_service.ingest_tiingo_5m_for_symbol",
                side_effect=_flaky_ingest,
            ),
        ):
            await _tiingo_5m_ingest_job()

        assert call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_rollback_on_outer_error(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "dal.market_data_dal.list_assets",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db error"),
        ):
            await _tiingo_5m_ingest_job()

        mock_session.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# _daily_yfinance_ingest_job
# ---------------------------------------------------------------------------

class TestDailyYfinanceIngestJob:
    """Verify _daily_yfinance_ingest_job fetches 1d bars for all active assets incrementally."""

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_ingests_active_assets_only(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        fake_assets = [
            {"id": 1, "symbol": "AAPL", "is_active": True},
            {"id": 2, "symbol": "MSFT", "is_active": True},
            {"id": 3, "symbol": "TSLA", "is_active": False},
        ]
        mock_ingest = AsyncMock(return_value={"symbol": "X", "timeframe": "1d", "inserted": 1})

        with (
            patch("dal.market_data_dal.list_assets", new_callable=AsyncMock, return_value=fake_assets),
            patch(
                "features.data_ingestion.ingest_service.ingest_ohlcv_for_symbol",
                mock_ingest,
            ),
        ):
            await _daily_yfinance_ingest_job()

        assert mock_ingest.call_count == 2
        for call in mock_ingest.call_args_list:
            args, kwargs = call
            assert args[2] == "1d"
            assert args[3] == "yfinance"
            assert kwargs.get("start") is None  # incremental
            assert kwargs.get("end") is None

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_skips_when_no_active_assets(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_ingest = AsyncMock()

        with (
            patch("dal.market_data_dal.list_assets", new_callable=AsyncMock, return_value=[]),
            patch(
                "features.data_ingestion.ingest_service.ingest_ohlcv_for_symbol",
                mock_ingest,
            ),
        ):
            await _daily_yfinance_ingest_job()

        mock_ingest.assert_not_called()

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_continues_on_symbol_error(self, mock_session_local):
        """A per-symbol error must not abort the whole job."""
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        fake_assets = [
            {"id": 1, "symbol": "AAPL", "is_active": True},
            {"id": 2, "symbol": "MSFT", "is_active": True},
        ]
        call_count = 0

        async def _flaky_ingest(session, symbol, timeframe, provider, start, end):
            nonlocal call_count
            call_count += 1
            if symbol == "AAPL":
                raise RuntimeError("yfinance rate limit")
            return {"symbol": symbol, "timeframe": "1d", "inserted": 2}

        with (
            patch("dal.market_data_dal.list_assets", new_callable=AsyncMock, return_value=fake_assets),
            patch(
                "features.data_ingestion.ingest_service.ingest_ohlcv_for_symbol",
                side_effect=_flaky_ingest,
            ),
        ):
            await _daily_yfinance_ingest_job()

        assert call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_rollback_on_outer_error(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "dal.market_data_dal.list_assets",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db error"),
        ):
            await _daily_yfinance_ingest_job()

        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    @patch("features.data_ingestion.scheduler.AsyncSessionLocal")
    async def test_no_tiingo_backfill_side_effect(self, mock_session_local):
        """Daily yfinance job must NOT trigger Tiingo 5m backfill (handled by its own job)."""
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        fake_assets = [{"id": 1, "symbol": "SPY", "is_active": True}]
        mock_tiingo = AsyncMock()

        with (
            patch("dal.market_data_dal.list_assets", new_callable=AsyncMock, return_value=fake_assets),
            patch(
                "features.data_ingestion.ingest_service.ingest_ohlcv_for_symbol",
                AsyncMock(return_value={"symbol": "SPY", "timeframe": "1d", "inserted": 1}),
            ),
            patch(
                "features.data_ingestion.ingest_service.ingest_tiingo_5m_for_symbol",
                mock_tiingo,
            ),
        ):
            await _daily_yfinance_ingest_job()

        mock_tiingo.assert_not_called()
