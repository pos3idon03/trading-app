"""Tests for live bar persistence."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.live_trading.bar_persistence import (
    bar_to_record,
    flush_bar_persist_queue,
    persist_completed_bar,
    set_persist_timeframes,
)
from features.live_trading.resampler import OHLCVBar


def _sample_bar(timeframe: str = "5m") -> OHLCVBar:
    start = datetime(2026, 5, 18, 14, 0, tzinfo=timezone.utc)
    end = datetime(2026, 5, 18, 14, 5, tzinfo=timezone.utc)
    return OHLCVBar(
        symbol="AAPL",
        timeframe=timeframe,
        open=100.0,
        high=101.0,
        low=99.5,
        close=100.5,
        volume=1200,
        vwap=100.2,
        bar_start=start,
        bar_end=end,
        tick_count=5,
    )


class TestBarToRecord:
    def test_maps_fields_for_db_insert(self):
        record = bar_to_record(_sample_bar(), asset_id=42)
        assert record.asset_id == 42
        assert record.timeframe == "5m"
        assert record.source == "alpaca"
        assert record.close == 100.5


class TestPersistCompletedBar:
    @pytest.mark.asyncio
    async def test_skips_when_timeframe_not_active(self):
        set_persist_timeframes(["1h"])
        with patch(
            "features.live_trading.bar_persistence.AsyncSessionLocal",
        ) as mock_session_local:
            await persist_completed_bar(_sample_bar("5m"))
        mock_session_local.assert_not_called()

    @pytest.mark.asyncio
    async def test_persists_when_timeframe_active(self):
        set_persist_timeframes(["5m"])
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "features.live_trading.bar_persistence.AsyncSessionLocal",
            return_value=ctx,
        ), patch(
            "features.live_trading.bar_persistence.get_asset_id_by_symbol",
            new=AsyncMock(return_value=7),
        ), patch(
            "features.live_trading.bar_persistence.bulk_insert_ohlcv",
            new=AsyncMock(return_value=1),
        ) as mock_insert:
            await persist_completed_bar(_sample_bar("5m"))
            await flush_bar_persist_queue()

        mock_insert.assert_awaited_once()
        session.commit.assert_awaited_once()
