"""Tests for MC intraday calibration helpers."""
import pytest

from features.quantitative_engine.mc_intraday import (
    default_calibration_days,
    is_intraday_timeframe,
    resolve_calibration_lookback_days,
)


class TestMcIntraday:
    def test_is_intraday_timeframe(self):
        assert is_intraday_timeframe("15m") is True
        assert is_intraday_timeframe("1d") is False

    def test_default_calibration_days(self):
        assert default_calibration_days("15m") == 30
        assert default_calibration_days("1h") == 60

    def test_resolve_intraday_caps_at_90(self):
        assert resolve_calibration_lookback_days("15m", calibration_years=10, calibration_days=120) == 90

    def test_resolve_intraday_uses_days_not_years(self):
        assert resolve_calibration_lookback_days("15m", calibration_years=10, calibration_days=30) == 30

    def test_resolve_daily_uses_years(self):
        assert resolve_calibration_lookback_days("1d", calibration_years=2) == 730

    def test_resolve_intraday_default_when_days_missing(self):
        assert resolve_calibration_lookback_days("5m", calibration_years=10) == 30
