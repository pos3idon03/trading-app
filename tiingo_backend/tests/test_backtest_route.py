from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_list_backtest_strategies():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/backtest/strategies")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["strategies"]) >= 5
    assert any(item["id"] == "sma_crossover" for item in data["strategies"])
    assert any(item["id"] == "strategy_ensemble" for item in data["strategies"])
    sma = next(item for item in data["strategies"] if item["id"] == "sma_crossover")
    assert sma["ensemble_eligible"] is True


@pytest.mark.asyncio
async def test_run_backtest_ensemble_accepts_nested_params():
    run_id = uuid4()
    mock_result = {
        "id": run_id,
        "symbol": "AAPL",
        "strategy": "strategy_ensemble",
        "status": "completed",
        "metrics": {
            "total_return_pct": 5.0,
            "benchmark_return_pct": 10.0,
            "alpha_pct": -5.0,
            "cagr_pct": 2.0,
            "max_drawdown_pct": 3.0,
            "sharpe_ratio": 0.5,
            "sortino_ratio": 0.7,
            "profit_factor": 1.2,
            "calmar_ratio": 0.67,
            "win_rate_pct": 50.0,
            "trade_count": 3,
            "final_equity": 10500.0,
            "initial_cash": 10000.0,
        },
    }

    with patch(
        "routes.backtest.run_backtest_for_symbol",
        new=AsyncMock(return_value=mock_result),
    ) as mock_run:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/backtest/run",
                json={
                    "symbol": "AAPL",
                    "strategy": "strategy_ensemble",
                    "params": {
                        "combine_mode": "majority",
                        "threshold": 0.5,
                        "legs": [
                            {
                                "strategy_id": "sma_crossover",
                                "params": {"fast_period": 20, "slow_period": 50},
                                "weight": 1.0,
                            },
                            {
                                "strategy_id": "rsi_reversion",
                                "params": {"period": 14, "oversold": 30, "overbought": 70},
                                "weight": 1.0,
                            },
                        ],
                    },
                },
            )

    assert resp.status_code == 200
    assert resp.json()["strategy"] == "strategy_ensemble"
    mock_run.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_backtest_success():
    run_id = uuid4()
    mock_result = {
        "id": run_id,
        "symbol": "AAPL",
        "strategy": "buy_and_hold",
        "status": "completed",
        "metrics": {
            "total_return_pct": 10.0,
            "benchmark_return_pct": 10.0,
            "alpha_pct": 0.0,
            "cagr_pct": 5.0,
            "max_drawdown_pct": 2.0,
            "sharpe_ratio": 1.2,
            "sortino_ratio": 1.5,
            "profit_factor": None,
            "calmar_ratio": 2.5,
            "win_rate_pct": 0.0,
            "trade_count": 0,
            "final_equity": 11000.0,
            "initial_cash": 10000.0,
        },
    }

    with patch(
        "routes.backtest.run_backtest_for_symbol",
        new=AsyncMock(return_value=mock_result),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/backtest/run",
                json={"symbol": "AAPL", "strategy": "buy_and_hold"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["status"] == "completed"
    assert data["metrics"]["total_return_pct"] == 10.0


@pytest.mark.asyncio
async def test_run_backtest_not_found():
    with patch(
        "routes.backtest.run_backtest_for_symbol",
        new=AsyncMock(side_effect=LookupError("Instrument not found: FAKE")),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/backtest/run",
                json={"symbol": "FAKE", "strategy": "buy_and_hold"},
            )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_backtest_results_success():
    run_id = uuid4()
    mock_row = {
        "id": run_id,
        "symbol": "AAPL",
        "strategy": "buy_and_hold",
        "params": {},
        "timeframe": "1d",
        "start_date": None,
        "end_date": None,
        "initial_cash": 10000.0,
        "commission_bps": 0.0,
        "status": "completed",
        "metrics": {
            "total_return_pct": 10.0,
            "benchmark_return_pct": 10.0,
            "alpha_pct": 0.0,
            "cagr_pct": 5.0,
            "max_drawdown_pct": 2.0,
            "sharpe_ratio": 1.2,
            "sortino_ratio": 1.5,
            "profit_factor": None,
            "calmar_ratio": 2.5,
            "win_rate_pct": 0.0,
            "trade_count": 0,
            "final_equity": 11000.0,
            "initial_cash": 10000.0,
        },
        "equity_curve": [
            {"date": "2024-01-01", "equity": 10000.0, "cash": 0.0, "shares": 100.0, "drawdown_pct": 0.0}
        ],
        "trades": [],
        "benchmark": {
            "equity_curve": [
                {"date": "2024-01-01", "equity": 10000.0, "cash": 0.0, "shares": 100.0, "drawdown_pct": 0.0}
            ]
        },
        "error_message": None,
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "finished_at": datetime(2024, 1, 2, tzinfo=timezone.utc),
    }

    with patch(
        "routes.backtest.get_backtest_results",
        new=AsyncMock(return_value=mock_row),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/backtest/{run_id}/results")

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert len(data["equity_curve"]) == 1


@pytest.mark.asyncio
async def test_get_backtest_results_not_found():
    with patch(
        "routes.backtest.get_backtest_results",
        new=AsyncMock(return_value=None),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/backtest/{uuid4()}/results")

    assert resp.status_code == 404
