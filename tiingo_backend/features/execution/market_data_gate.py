from datetime import datetime, timezone


def is_ohlcv_ready_for_evaluation(readiness: dict) -> bool:
    expected = readiness.get("expected_latest_bar_time")
    latest = readiness.get("ohlcv_latest_bar_time")
    if expected is None:
        return True
    if latest is None:
        return False
    return latest.astimezone(timezone.utc) >= expected.astimezone(timezone.utc)


def market_data_not_ready_reason(readiness: dict) -> str:
    expected = readiness.get("expected_latest_bar_time")
    latest = readiness.get("ohlcv_latest_bar_time")
    if isinstance(expected, datetime):
        expected_s = expected.astimezone(timezone.utc).isoformat()
    else:
        expected_s = "unknown"
    if isinstance(latest, datetime):
        latest_s = latest.astimezone(timezone.utc).isoformat()
    else:
        latest_s = "none"
    return (
        "Market data not ready for latest bar "
        f"(ohlcv_latest={latest_s}, expected={expected_s})"
    )
