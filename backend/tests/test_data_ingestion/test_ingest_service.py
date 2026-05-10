"""Unit tests for ingest_service incremental start-date logic."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.data_ingestion.ingest_service import ingest_ohlcv_for_symbol


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session() -> MagicMock:
    return MagicMock()


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Incremental start-date logic
# ---------------------------------------------------------------------------

class TestIncrementalStartDate:
    """Verify that the fetch start is advanced by one timeframe unit past
    the latest stored bar so no duplicate bar is ever re-requested."""

    async def _run(
        self,
        timeframe: str,
        latest: datetime | None,
    ) -> datetime:
        """Run ingest_ohlcv_for_symbol and return the start datetime that was
        passed to the provider's fetch_ohlcv."""
        captured = {}

        mock_provider = MagicMock()
        mock_provider.fetch_ohlcv = AsyncMock(return_value=[])

        async def _capture_fetch(symbol, tf, start, end, asset_id=None):
            captured["start"] = start
            return []

        mock_provider.fetch_ohlcv.side_effect = _capture_fetch

        with (
            patch(
                "features.data_ingestion.ingest_service.get_provider",
                return_value=mock_provider,
            ),
            patch(
                "features.data_ingestion.ingest_service.upsert_asset",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "features.data_ingestion.ingest_service.get_latest_timestamp",
                new=AsyncMock(return_value=latest),
            ),
            patch(
                "features.data_ingestion.ingest_service.bulk_insert_ohlcv",
                new=AsyncMock(return_value=0),
            ),
        ):
            await ingest_ohlcv_for_symbol(
                session=_make_session(),
                symbol="AAPL",
                timeframe=timeframe,
                provider_name="yfinance",
                start=None,
                end=None,
            )

        return captured["start"]

    @pytest.mark.asyncio
    async def test_daily_incremental_advances_one_day(self):
        latest = _utc(2024, 1, 10)
        start = await self._run("1d", latest)
        assert start == _utc(2024, 1, 11), f"Expected 2024-01-11, got {start}"

    @pytest.mark.asyncio
    async def test_hourly_incremental_advances_one_hour(self):
        latest = _utc(2024, 1, 10, hour=9)
        start = await self._run("1h", latest)
        assert start == _utc(2024, 1, 10, hour=10), f"Expected 10:00, got {start}"

    @pytest.mark.asyncio
    async def test_5m_incremental_advances_five_minutes(self):
        latest = datetime(2024, 1, 10, 9, 30, tzinfo=timezone.utc)
        start = await self._run("5m", latest)
        expected = datetime(2024, 1, 10, 9, 35, tzinfo=timezone.utc)
        assert start == expected, f"Expected 09:35, got {start}"

    @pytest.mark.asyncio
    async def test_weekly_incremental_advances_one_week(self):
        latest = _utc(2024, 1, 8)
        start = await self._run("1w", latest)
        assert start == _utc(2024, 1, 15), f"Expected 2024-01-15, got {start}"

    @pytest.mark.asyncio
    async def test_first_ingestion_uses_epoch_start(self):
        """When no data exists yet (latest=None) start at 1970-01-01."""
        start = await self._run("1d", latest=None)
        assert start == datetime(1970, 1, 1, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_explicit_start_overrides_latest(self):
        """When caller provides an explicit start_date it must be used as-is,
        ignoring get_latest_timestamp entirely."""
        captured = {}

        mock_provider = MagicMock()

        async def _capture_fetch(symbol, tf, start, end, asset_id=None):
            captured["start"] = start
            return []

        mock_provider.fetch_ohlcv.side_effect = _capture_fetch

        explicit_start = _utc(2023, 6, 1)

        with (
            patch(
                "features.data_ingestion.ingest_service.get_provider",
                return_value=mock_provider,
            ),
            patch(
                "features.data_ingestion.ingest_service.upsert_asset",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "features.data_ingestion.ingest_service.get_latest_timestamp",
                new=AsyncMock(return_value=_utc(2024, 1, 10)),
            ),
            patch(
                "features.data_ingestion.ingest_service.bulk_insert_ohlcv",
                new=AsyncMock(return_value=0),
            ),
        ):
            await ingest_ohlcv_for_symbol(
                session=_make_session(),
                symbol="MSFT",
                timeframe="1d",
                provider_name="yfinance",
                start=explicit_start,
                end=None,
            )

        assert captured["start"] == explicit_start
