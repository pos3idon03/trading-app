from datetime import datetime, timedelta, timezone

import pytest

from features.market_data.ohlcv_resample import (
    SUPPORTED_TIMEFRAMES,
    compute_resample_start,
    is_tail_timeframe,
    resolve_ohlcv_query,
)


class TestResolveOhlcvQuery:
    @pytest.mark.parametrize("tf", ["1m", "5m", "1d"])
    def test_native_timeframes_have_no_bucket(self, tf):
        plan = resolve_ohlcv_query(tf)
        assert plan.source_timeframe == tf
        assert plan.bucket_interval is None

    @pytest.mark.parametrize("tf,minutes", [("15m", 15), ("30m", 30)])
    def test_intraday_resample_from_1m(self, tf, minutes):
        plan = resolve_ohlcv_query(tf)
        assert plan.source_timeframe == "1m"
        assert plan.bucket_interval == timedelta(minutes=minutes)

    def test_1h_resample(self):
        plan = resolve_ohlcv_query("1h")
        assert plan.source_timeframe == "1m"
        assert plan.bucket_interval == timedelta(hours=1)

    def test_4h_resample(self):
        plan = resolve_ohlcv_query("4h")
        assert plan.bucket_interval == timedelta(hours=4)

    def test_1w_resample_from_daily(self):
        plan = resolve_ohlcv_query("1w")
        assert plan.source_timeframe == "1d"
        assert plan.bucket_interval == timedelta(weeks=1)

    def test_1mo_resample_from_daily(self):
        plan = resolve_ohlcv_query("1mo")
        assert plan.source_timeframe == "1d"
        assert plan.bucket_interval == "1 month"

    def test_unsupported_timeframe_raises(self):
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            resolve_ohlcv_query("2h")

    def test_supported_set_covers_all_dashboard_timeframes(self):
        expected = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1mo"}
        assert expected == SUPPORTED_TIMEFRAMES


class TestComputeResampleStart:
    def test_uses_explicit_start_when_provided(self):
        end = datetime(2024, 6, 1, tzinfo=timezone.utc)
        explicit = datetime(2024, 1, 1, tzinfo=timezone.utc)
        result = compute_resample_start(
            end, 3000, timedelta(minutes=15), explicit_start=explicit,
        )
        assert result == explicit

    def test_computes_window_from_bucket_and_limit(self):
        end = datetime(2024, 6, 1, tzinfo=timezone.utc)
        result = compute_resample_start(end, 100, timedelta(hours=1))
        expected = end - timedelta(hours=int(100 * 1.2))
        assert result == expected

    def test_monthly_window_uses_day_estimate(self):
        end = datetime(2024, 6, 1, tzinfo=timezone.utc)
        result = compute_resample_start(end, 24, "1 month")
        assert result < end
        assert (end - result).days >= 24 * 31


class TestIsTailTimeframe:
    def test_intraday_is_tail(self):
        assert is_tail_timeframe("15m") is True
        assert is_tail_timeframe("1h") is True

    def test_daily_plus_is_not_tail(self):
        assert is_tail_timeframe("1d") is False
        assert is_tail_timeframe("1w") is False
        assert is_tail_timeframe("1mo") is False
