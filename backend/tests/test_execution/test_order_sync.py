"""Tests for order sync helpers."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from features.execution.broker_client import OrderResult, is_terminal_order_status
from features.execution.order_sync import parse_filled_at, wait_for_order_terminal


class TestIsTerminalOrderStatus:
    def test_filled_is_terminal(self):
        assert is_terminal_order_status("filled") is True

    def test_pending_new_is_not_terminal(self):
        assert is_terminal_order_status("pending_new") is False

    def test_accepted_is_not_terminal(self):
        assert is_terminal_order_status("accepted") is False


class TestWaitForOrderTerminal:
    def test_returns_initial_when_already_terminal(self):
        initial = OrderResult(
            order_id="abc",
            symbol="AAPL",
            side="buy",
            qty=1,
            order_type="market",
            status="filled",
            filled_price=100.0,
            filled_qty=1,
        )
        result = wait_for_order_terminal("abc", initial, max_wait_sec=0.1)
        assert result.status == "filled"

    @patch("features.execution.order_sync.fetch_order_by_id")
    @patch("features.execution.order_sync.time.sleep")
    def test_polls_until_filled(self, mock_sleep, mock_fetch):
        pending = OrderResult(
            order_id="abc", symbol="AAPL", side="buy", qty=1,
            order_type="market", status="pending_new",
        )
        filled = OrderResult(
            order_id="abc", symbol="AAPL", side="buy", qty=1,
            order_type="market", status="filled",
            filled_price=99.5, filled_qty=1,
        )
        mock_fetch.return_value = filled
        result = wait_for_order_terminal("abc", pending, max_wait_sec=5.0)
        assert result.status == "filled"
        assert result.filled_price == 99.5
        mock_fetch.assert_called()


class TestParseFilledAt:
    def test_uses_broker_timestamp(self):
        ts = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
        result = OrderResult(
            order_id="x", symbol="AAPL", side="buy", qty=1,
            order_type="market", status="filled", filled_at=ts,
        )
        assert parse_filled_at(result) == ts

    def test_filled_without_timestamp_gets_now(self):
        result = OrderResult(
            order_id="x", symbol="AAPL", side="buy", qty=1,
            order_type="market", status="filled",
        )
        assert parse_filled_at(result) is not None
