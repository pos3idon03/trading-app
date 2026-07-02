from datetime import datetime, timezone

import pytest

from features.execution.deployment_timeframes import (
    EXECUTION_TIMEFRAMES,
    due_execution_timeframes,
    floor_to_cron_slot,
    ingest_source_for_asset,
    native_fetch_timeframe,
    should_evaluate_timeframe,
    tiingo_source_for_asset,
    validate_execution_timeframe,
)


def test_execution_timeframes_set():
    assert EXECUTION_TIMEFRAMES == frozenset({"5m", "15m", "30m", "1h", "4h", "1d", "1w", "1mo"})


def test_validate_execution_timeframe_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported deployment timeframe"):
        validate_execution_timeframe("1m")


@pytest.mark.parametrize(
    ("deployment_tf", "native_tf", "source"),
    [
        ("5m", "5m", "tiingo_iex"),
        ("4h", "1h", "tiingo_iex"),
        ("1d", "1d", "tiingo_eod"),
        ("1w", "1d", "tiingo_eod"),
    ],
)
def test_native_fetch_and_source(deployment_tf, native_tf, source):
    assert native_fetch_timeframe(deployment_tf) == native_tf
    assert tiingo_source_for_asset("stock", native_tf) == source


def test_crypto_uses_tiingo_crypto():
    assert tiingo_source_for_asset("crypto", "1d") == "tiingo_crypto"


def test_crypto_intraday_ingest_prefers_alpaca_by_default():
    assert ingest_source_for_asset("crypto", "1h") == "alpaca_crypto"
    assert ingest_source_for_asset("crypto", "5m") == "alpaca_crypto"


def test_crypto_daily_ingest_keeps_tiingo():
    assert ingest_source_for_asset("crypto", "1d") == "tiingo_crypto"


def test_crypto_intraday_ingest_respects_tiingo_setting(monkeypatch):
    monkeypatch.setenv("CRYPTO_INTRADAY_SOURCE", "tiingo")
    from config import get_settings

    get_settings.cache_clear()
    assert ingest_source_for_asset("crypto", "1h") == "tiingo_crypto"
    get_settings.cache_clear()


def test_intraday_boundary_during_session():
    as_of = datetime(2026, 5, 28, 15, 0, tzinfo=timezone.utc)
    assert should_evaluate_timeframe("5m", as_of) is True
    assert should_evaluate_timeframe("15m", as_of) is True
    assert should_evaluate_timeframe("1h", as_of) is True


def test_stock_1h_runs_at_21_utc_closing_slot():
    as_of = datetime(2026, 5, 28, 21, 0, tzinfo=timezone.utc)
    assert should_evaluate_timeframe("1h", as_of, asset_type="stock") is True


def test_stock_1h_skipped_after_21_utc_non_boundary():
    as_of = datetime(2026, 5, 28, 21, 5, tzinfo=timezone.utc)
    assert should_evaluate_timeframe("1h", as_of, asset_type="stock") is False


def test_intraday_skipped_outside_session():
    as_of = datetime(2026, 5, 28, 2, 0, tzinfo=timezone.utc)
    assert should_evaluate_timeframe("5m", as_of) is False


def test_crypto_intraday_runs_outside_us_session():
    as_of = datetime(2026, 5, 28, 2, 0, tzinfo=timezone.utc)
    assert should_evaluate_timeframe("1h", as_of, asset_type="crypto") is True
    assert should_evaluate_timeframe("1h", as_of, asset_type="stock") is False


def test_daily_boundary():
    as_of = datetime(2026, 5, 28, 22, 15, tzinfo=timezone.utc)
    assert should_evaluate_timeframe("1d", as_of) is True
    assert should_evaluate_timeframe("5m", as_of) is False


def test_weekly_boundary():
    as_of = datetime(2026, 6, 1, 22, 15, tzinfo=timezone.utc)
    assert should_evaluate_timeframe("1w", as_of) is True


def test_monthly_boundary():
    as_of = datetime(2026, 6, 1, 22, 20, tzinfo=timezone.utc)
    assert should_evaluate_timeframe("1mo", as_of) is True


def test_due_execution_timeframes_filters():
    as_of = datetime(2026, 5, 28, 22, 15, tzinfo=timezone.utc)
    due = due_execution_timeframes(as_of)
    assert "1d" in due
    assert "5m" not in due


@pytest.mark.parametrize("minute", [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
def test_cron_aligned_minutes_include_5m_during_session(minute):
    as_of = datetime(2026, 5, 28, 15, minute, tzinfo=timezone.utc)
    assert should_evaluate_timeframe("5m", as_of) is True


def test_non_cron_aligned_minute_skips_5m():
    as_of = datetime(2026, 5, 28, 15, 3, tzinfo=timezone.utc)
    assert should_evaluate_timeframe("5m", as_of) is False


def test_floor_to_cron_slot_rounds_down():
    dt = datetime(2026, 5, 28, 14, 7, tzinfo=timezone.utc)
    assert floor_to_cron_slot(dt) == datetime(2026, 5, 28, 14, 5, tzinfo=timezone.utc)
