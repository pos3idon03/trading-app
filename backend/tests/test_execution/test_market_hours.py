"""Tests for US equity RTH market hours guard."""
from datetime import datetime
from zoneinfo import ZoneInfo

from features.execution.market_hours import is_us_equity_rth_open, should_skip_order_for_asset_type

_NY = ZoneInfo("America/New_York")


class TestIsUsEquityRthOpen:
    def test_open_mid_session_weekday(self):
        dt = datetime(2026, 5, 20, 11, 0, tzinfo=_NY)
        assert is_us_equity_rth_open(dt) is True

    def test_closed_on_weekend(self):
        dt = datetime(2026, 5, 23, 12, 0, tzinfo=_NY)
        assert is_us_equity_rth_open(dt) is False

    def test_closed_before_open(self):
        dt = datetime(2026, 5, 20, 8, 0, tzinfo=_NY)
        assert is_us_equity_rth_open(dt) is False


class TestShouldSkipOrderForAssetType:
    def test_stock_requires_rth(self):
        assert should_skip_order_for_asset_type("stock") is True

    def test_crypto_does_not(self):
        assert should_skip_order_for_asset_type("crypto") is False
