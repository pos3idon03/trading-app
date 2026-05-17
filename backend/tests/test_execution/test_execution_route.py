"""Tests for execution routes."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestExecutionStatusEndpoint:
    @patch("routes.execution.get_stream")
    @patch("routes.execution.get_risk_manager")
    def test_get_status(self, mock_risk, mock_stream):
        mock_risk.return_value.config = MagicMock(kill_switch_active=False)
        mock_status = MagicMock(connected=False, subscribed_symbols=[])
        mock_stream.return_value.status = mock_status

        response = client.get("/api/v1/execution/status")
        assert response.status_code == 200
        data = response.json()
        assert data["trading_mode"] == "paper"
        assert data["kill_switch_active"] is False


class TestRiskConfigEndpoint:
    @patch("routes.execution.get_risk_manager")
    def test_get_risk_config(self, mock_risk):
        mock_risk.return_value.config = MagicMock(
            max_position_pct=5.0,
            max_exposure_pct=80.0,
            daily_loss_limit_pct=5.0,
            max_orders_per_minute=10,
            kill_switch_active=False,
        )

        response = client.get("/api/v1/execution/risk/config")
        assert response.status_code == 200
        data = response.json()
        assert data["max_position_pct"] == 5.0
        assert data["max_exposure_pct"] == 80.0


class TestOrderHistoryEndpoint:
    @patch("routes.execution.execution_dal")
    def test_empty_history(self, mock_dal):
        mock_dal.get_order_history = AsyncMock(return_value=([], 0))

        response = client.get("/api/v1/execution/orders")
        assert response.status_code == 200
        data = response.json()
        assert data["orders"] == []
        assert data["total"] == 0

    @patch("routes.execution.refresh_open_orders_from_alpaca", new_callable=AsyncMock)
    @patch("routes.execution.execution_dal")
    def test_paginated_history(self, mock_dal, _mock_refresh):
        mock_order = MagicMock(
            id=11,
            asset_id=1,
            symbol="BTCUSD",
            side="buy",
            qty=0.1,
            order_type="market",
            limit_price=None,
            stop_price=None,
            status="filled",
            alpaca_order_id="alp-11",
            filled_price=100.0,
            filled_qty=0.1,
            filled_at=None,
            signal_id=None,
            error_message=None,
            created_at=None,
            updated_at=None,
        )
        mock_dal.get_order_history = AsyncMock(return_value=([mock_order], 25))

        response = client.get("/api/v1/execution/orders?limit=10&offset=10")

        assert response.status_code == 200
        mock_dal.get_order_history.assert_awaited_once()
        call_kwargs = mock_dal.get_order_history.await_args.kwargs
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 10
        data = response.json()
        assert data["total"] == 25
        assert len(data["orders"]) == 1
        assert data["orders"][0]["id"] == 11


class TestPortfolioEndpoint:
    @patch("routes.execution.get_portfolio_summary")
    def test_get_portfolio(self, mock_summary):
        mock_summary.return_value = {
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 100000.0,
            "portfolio_value": 100000.0,
            "daily_pnl": 500.0,
            "daily_pnl_pct": 0.5,
            "total_positions": 2,
            "positions": [
                {
                    "symbol": "AAPL",
                    "qty": 10,
                    "market_value": 1500.0,
                    "avg_entry_price": 145.0,
                    "current_price": 150.0,
                    "unrealized_pnl": 50.0,
                    "unrealized_pnl_pct": 0.034,
                }
            ],
        }

        response = client.get("/api/v1/execution/portfolio")
        assert response.status_code == 200
        data = response.json()
        assert data["equity"] == 100000.0
        assert len(data["positions"]) == 1

    @patch("routes.execution.get_portfolio_summary")
    def test_portfolio_error(self, mock_summary):
        mock_summary.return_value = {"error": "Could not fetch"}

        response = client.get("/api/v1/execution/portfolio")
        assert response.status_code == 200
        data = response.json()
        assert data["equity"] == 0


class TestRiskEventsEndpoint:
    @patch("routes.execution.execution_dal")
    def test_empty_events(self, mock_dal):
        mock_dal.get_risk_events = AsyncMock(return_value=([], 0))

        response = client.get("/api/v1/execution/risk/events")
        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["total"] == 0
