"""Tests for the broker client (mocked Alpaca API)."""
from unittest.mock import MagicMock, patch

import pytest

from features.execution.broker_client import (
    AccountInfo,
    OrderResult,
    Position,
    cancel_order,
    get_account,
    get_positions,
    submit_limit_order,
    submit_market_order,
    submit_stop_loss,
)


def _mock_order(
    order_id="test-123",
    symbol="AAPL",
    side="buy",
    qty=10,
    order_type="market",
    status="accepted",
):
    order = MagicMock()
    order.id = order_id
    order.symbol = symbol
    order.side = MagicMock(value=side)
    order.qty = qty
    order.order_type = MagicMock(value=order_type)
    order.status = MagicMock(value=status)
    order.filled_avg_price = None
    order.filled_qty = None
    order.limit_price = None
    order.stop_price = None
    return order


class TestSubmitMarketOrder:
    @patch("features.execution.broker_client._get_trading_client")
    def test_success(self, mock_client):
        mock_client.return_value.submit_order.return_value = _mock_order()

        result = submit_market_order("AAPL", 10, "buy")
        assert isinstance(result, OrderResult)
        assert result.order_id == "test-123"
        assert result.symbol == "AAPL"
        assert result.status == "accepted"
        assert result.error is None

    @patch("features.execution.broker_client._get_trading_client")
    def test_failure(self, mock_client):
        mock_client.return_value.submit_order.side_effect = Exception("Insufficient funds")

        result = submit_market_order("AAPL", 10, "buy")
        assert result.status == "rejected"
        assert "Insufficient funds" in result.error


class TestSubmitLimitOrder:
    @patch("features.execution.broker_client._get_trading_client")
    def test_success(self, mock_client):
        order = _mock_order(order_type="limit")
        order.limit_price = 150.0
        mock_client.return_value.submit_order.return_value = order

        result = submit_limit_order("AAPL", 10, "buy", 150.0)
        assert isinstance(result, OrderResult)
        assert result.limit_price == 150.0


class TestSubmitStopLoss:
    @patch("features.execution.broker_client._get_trading_client")
    def test_success(self, mock_client):
        order = _mock_order(order_type="stop", side="sell")
        order.stop_price = 140.0
        mock_client.return_value.submit_order.return_value = order

        result = submit_stop_loss("AAPL", 10, 140.0)
        assert isinstance(result, OrderResult)
        assert result.stop_price == 140.0


class TestCancelOrder:
    @patch("features.execution.broker_client._get_trading_client")
    def test_success(self, mock_client):
        mock_client.return_value.cancel_order_by_id.return_value = None
        assert cancel_order("test-123") is True

    @patch("features.execution.broker_client._get_trading_client")
    def test_failure(self, mock_client):
        mock_client.return_value.cancel_order_by_id.side_effect = Exception("Not found")
        assert cancel_order("test-123") is False


class TestGetPositions:
    @patch("features.execution.broker_client._get_trading_client")
    def test_returns_positions(self, mock_client):
        pos = MagicMock()
        pos.symbol = "AAPL"
        pos.qty = 10
        pos.market_value = 1500.0
        pos.avg_entry_price = 145.0
        pos.current_price = 150.0
        pos.unrealized_pl = 50.0
        pos.unrealized_plpc = 0.034

        mock_client.return_value.get_all_positions.return_value = [pos]

        positions = get_positions()
        assert len(positions) == 1
        assert isinstance(positions[0], Position)
        assert positions[0].symbol == "AAPL"

    @patch("features.execution.broker_client._get_trading_client")
    def test_error_returns_empty(self, mock_client):
        mock_client.return_value.get_all_positions.side_effect = Exception("API error")
        positions = get_positions()
        assert positions == []


class TestGetAccount:
    @patch("features.execution.broker_client._get_trading_client")
    def test_success(self, mock_client):
        acct = MagicMock()
        acct.equity = "100000.00"
        acct.cash = "50000.00"
        acct.buying_power = "100000.00"
        acct.portfolio_value = "100000.00"
        acct.daytrade_count = "0"

        mock_client.return_value.get_account.return_value = acct
        result = get_account()
        assert isinstance(result, AccountInfo)
        assert result.equity == 100000.0

    @patch("features.execution.broker_client._get_trading_client")
    def test_error_returns_none(self, mock_client):
        mock_client.return_value.get_account.side_effect = Exception("API error")
        assert get_account() is None
