"""Tests for merged OHLCV bar resolution."""
from datetime import datetime, timezone
from types import SimpleNamespace

from features.live_trading.bar_resolution import bar_timestamp_key, merge_bars
from features.live_trading.resampler import OHLCVBar


def _db_bar(time_str: str, close: float) -> SimpleNamespace:
    return SimpleNamespace(
        open=close - 1,
        high=close + 1,
        low=close - 2,
        close=close,
        volume=100,
        bar_start=time_str,
    )


def _resampler_bar(time_str: str, close: float) -> OHLCVBar:
    start = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    return OHLCVBar(
        symbol="AAPL",
        timeframe="5m",
        open=close - 1,
        high=close + 1,
        low=close - 2,
        close=close,
        volume=100,
        vwap=None,
        bar_start=start,
        bar_end=start,
        tick_count=1,
    )


class TestMergeBars:
    def test_resampler_overrides_db_on_same_timestamp(self):
        db = [_db_bar("2026-05-18T14:00:00+00:00", 100.0)]
        live = [_resampler_bar("2026-05-18T14:00:00+00:00", 101.0)]
        merged = merge_bars(db, live)
        assert len(merged) == 1
        assert merged[0].close == 101.0

    def test_appends_newer_resampler_bars(self):
        db = [_db_bar("2026-05-18T14:00:00+00:00", 100.0)]
        live = [_resampler_bar("2026-05-18T14:05:00+00:00", 102.0)]
        merged = merge_bars(db, live)
        assert len(merged) == 2
        assert merged[-1].close == 102.0

    def test_bar_timestamp_key_handles_string_and_datetime(self):
        bar = _resampler_bar("2026-05-18T14:00:00+00:00", 100.0)
        assert "2026-05-18" in bar_timestamp_key(bar)
