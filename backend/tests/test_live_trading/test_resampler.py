"""Tests for the resampling engine."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from features.live_trading.resampler import (
    OHLCVBar,
    ResamplingEngine,
    _align_bar_start,
    _BarBuffer,
    _update_buffer,
    TIMEFRAME_DELTAS,
)


class TestAlignBarStart:
    def test_30m_alignment(self):
        ts = datetime(2024, 1, 15, 10, 17, 30, tzinfo=timezone.utc)
        aligned = _align_bar_start(ts, timedelta(minutes=30))
        assert aligned == datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    def test_1h_alignment(self):
        ts = datetime(2024, 1, 15, 10, 45, 0, tzinfo=timezone.utc)
        aligned = _align_bar_start(ts, timedelta(hours=1))
        assert aligned == datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    def test_4h_alignment(self):
        ts = datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
        aligned = _align_bar_start(ts, timedelta(hours=4))
        assert aligned == datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc)

    def test_1d_alignment(self):
        ts = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        aligned = _align_bar_start(ts, timedelta(days=1))
        assert aligned == datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)


class TestUpdateBuffer:
    def test_first_tick(self):
        buf = _BarBuffer()
        _update_buffer(buf, 100.0, 500, None)
        assert buf.open == 100.0
        assert buf.high == 100.0
        assert buf.low == 100.0
        assert buf.close == 100.0
        assert buf.volume == 500
        assert buf.tick_count == 1

    def test_multiple_ticks(self):
        buf = _BarBuffer()
        _update_buffer(buf, 100.0, 500, None)
        _update_buffer(buf, 105.0, 300, None)
        _update_buffer(buf, 95.0, 200, None)
        assert buf.open == 100.0
        assert buf.high == 105.0
        assert buf.low == 95.0
        assert buf.close == 95.0
        assert buf.volume == 1000
        assert buf.tick_count == 3

    def test_vwap_accumulation(self):
        buf = _BarBuffer()
        _update_buffer(buf, 100.0, 500, 100.0)
        _update_buffer(buf, 102.0, 300, 101.0)
        expected_numerator = 100.0 * 500 + 101.0 * 300
        assert buf.vwap_numerator == pytest.approx(expected_numerator)


@pytest.mark.asyncio
class TestResamplingEngine:
    async def test_single_tick_no_bar(self):
        engine = ResamplingEngine(timeframes=["1h"])
        bars = await engine.process_tick(
            "AAPL", 150.0, 1000,
            datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )
        assert len(bars) == 0

    async def test_bar_emitted_on_period_change(self):
        engine = ResamplingEngine(timeframes=["1h"])

        await engine.process_tick(
            "AAPL", 150.0, 1000,
            datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )
        await engine.process_tick(
            "AAPL", 152.0, 500,
            datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )

        bars = await engine.process_tick(
            "AAPL", 151.0, 800,
            datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
        )

        assert len(bars) == 1
        bar = bars[0]
        assert bar.symbol == "AAPL"
        assert bar.timeframe == "1h"
        assert bar.open == 150.0
        assert bar.high == 152.0
        assert bar.close == 152.0
        assert bar.volume == 1500

    async def test_multiple_timeframes(self):
        engine = ResamplingEngine(timeframes=["30m", "1h"])

        await engine.process_tick(
            "AAPL", 150.0, 1000,
            datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        bars = await engine.process_tick(
            "AAPL", 151.0, 500,
            datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )

        assert len(bars) == 1
        assert bars[0].timeframe == "30m"

    async def test_get_bars_returns_history(self):
        engine = ResamplingEngine(timeframes=["1h"])

        for hour in range(10, 15):
            await engine.process_tick(
                "AAPL", 150.0 + hour, 1000,
                datetime(2024, 1, 15, hour, 0, 0, tzinfo=timezone.utc),
            )

        bars = engine.get_bars("AAPL", "1h")
        assert len(bars) >= 3

    async def test_callback_fired_on_bar(self):
        engine = ResamplingEngine(timeframes=["1h"])
        received: list[OHLCVBar] = []

        async def on_bar(bar: OHLCVBar):
            received.append(bar)

        engine.on_bar(on_bar)

        await engine.process_tick("AAPL", 150.0, 1000, datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc))
        await engine.process_tick("AAPL", 151.0, 500, datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc))

        assert len(received) == 1
        assert received[0].symbol == "AAPL"
