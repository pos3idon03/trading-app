from datetime import datetime, timezone

from features.execution.market_data_gate import (
    is_ohlcv_ready_for_evaluation,
    market_data_not_ready_reason,
)


def test_is_ohlcv_ready_when_latest_meets_expected():
    readiness = {
        "expected_latest_bar_time": datetime(2026, 5, 28, 19, 0, tzinfo=timezone.utc),
        "ohlcv_latest_bar_time": datetime(2026, 5, 28, 19, 0, tzinfo=timezone.utc),
    }
    assert is_ohlcv_ready_for_evaluation(readiness) is True


def test_is_ohlcv_not_ready_when_latest_behind():
    readiness = {
        "expected_latest_bar_time": datetime(2026, 5, 28, 20, 0, tzinfo=timezone.utc),
        "ohlcv_latest_bar_time": datetime(2026, 5, 28, 19, 0, tzinfo=timezone.utc),
    }
    assert is_ohlcv_ready_for_evaluation(readiness) is False
    assert "Market data not ready" in market_data_not_ready_reason(readiness)
