from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from db import get_db
from routes import execution


async def _fake_db_session():
    yield AsyncMock()


@pytest.mark.asyncio
async def test_delete_deployment_route(monkeypatch):
    deployment_id = uuid4()
    monkeypatch.setattr(
        execution,
        "delete_deployment",
        AsyncMock(
            return_value={
                "deleted": True,
                "close_positions": True,
                "closed_qty": 2.0,
                "close_order_id": None,
            }
        ),
    )
    app = FastAPI()
    app.dependency_overrides[get_db] = _fake_db_session
    app.include_router(execution.router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(
            "DELETE",
            f"/api/v1/execution/deployments/{deployment_id}",
            json={"close_positions": True},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] is True
    assert data["close_positions"] is True
    assert data["closed_qty"] == 2.0


@pytest.mark.asyncio
async def test_execution_status_endpoint(monkeypatch):
    monkeypatch.setattr(
        execution,
        "get_execution_status",
        AsyncMock(
            return_value={
                "trading_mode": "paper",
                "alpaca_configured": False,
                "alpaca_base_url": "https://paper-api.alpaca.markets",
                "kill_switch_enabled": False,
                "paper_trading_only": True,
                "trading_mode_paper": True,
            }
        ),
    )
    app = FastAPI()
    app.include_router(execution.router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/execution/status")
    assert response.status_code == 200
    data = response.json()
    assert data["trading_mode"] == "paper"
    assert data["kill_switch_enabled"] is False


@pytest.mark.asyncio
async def test_risk_config_endpoint():
    app = FastAPI()
    app.include_router(execution.router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/execution/risk-config")
    assert response.status_code == 200
    data = response.json()
    assert data["max_position_pct"] > 0


@pytest.mark.asyncio
async def test_overview_endpoint(monkeypatch):
    deployment_id = uuid4()
    model_id = uuid4()
    monkeypatch.setattr(
        execution,
        "get_deployment_overview",
        AsyncMock(
            return_value=[
                {
                    "id": deployment_id,
                    "model_id": model_id,
                    "symbol": "AAPL",
                    "timeframe": "5m",
                    "status": "active",
                    "model_name": "AAPL model",
                    "last_signal": "hold",
                    "last_probability": 0.457,
                    "buy_threshold": 0.55,
                    "sell_threshold": 0.45,
                    "last_explainability": {
                        "method": "shap_linear",
                        "top_contributors": [
                            {"feature": "ret_5", "value": 0.03, "contribution": 0.08},
                        ],
                        "warnings": [],
                    },
                    "last_evaluated_bar_time": None,
                    "current_price": 190.5,
                    "price_updated_at": None,
                    "round_trip_count": 0,
                    "open_position_count": 0,
                    "order_count": 0,
                    "open_order_count": 0,
                    "strategy_profit": 0.0,
                    "strategy_profit_pct": None,
                    "position_qty": 0.0,
                    "position_side": "flat",
                    "update_status": "current",
                    "expected_latest_bar_time": None,
                    "ohlcv_latest_bar_time": None,
                    "missed_slot_count": 0,
                },
            ],
        ),
    )
    app = FastAPI()
    app.dependency_overrides[get_db] = _fake_db_session
    app.include_router(execution.router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/execution/overview")
    assert response.status_code == 200
    data = response.json()
    assert len(data["deployments"]) == 1
    assert data["deployments"][0]["symbol"] == "AAPL"
    assert data["deployments"][0]["last_signal"] == "hold"
    assert data["deployments"][0]["buy_threshold"] == 0.55
    assert data["deployments"][0]["sell_threshold"] == 0.45
    assert data["deployments"][0]["last_explainability"]["method"] == "shap_linear"
    assert data["deployments"][0]["update_status"] == "current"


@pytest.mark.asyncio
async def test_refresh_deployment_route(monkeypatch):
    deployment_id = uuid4()
    monkeypatch.setattr(
        execution,
        "get_deployment",
        AsyncMock(
            return_value={
                "id": deployment_id,
                "symbol": "IBM",
                "timeframe": "1h",
            },
        ),
    )
    monkeypatch.setattr(
        execution,
        "refresh_deployment_market_data",
        AsyncMock(return_value={"results": [{"symbol": "IBM", "status": "ok"}]}),
    )
    app = FastAPI()
    app.dependency_overrides[get_db] = _fake_db_session
    app.include_router(execution.router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/execution/deployments/{deployment_id}/refresh")
    assert response.status_code == 200
    assert response.json()["deployment_id"] == str(deployment_id)


@pytest.mark.asyncio
async def test_enqueue_market_data_refresh(monkeypatch):
    job_id = uuid4()
    monkeypatch.setattr(
        execution,
        "create_and_enqueue_job",
        AsyncMock(return_value={"id": job_id, "status": "pending"}),
    )
    app = FastAPI()
    app.dependency_overrides[get_db] = _fake_db_session
    app.include_router(execution.router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/execution/market-data/refresh/enqueue")
    assert response.status_code == 202
    assert response.json()["job_id"] == str(job_id)


@pytest.mark.asyncio
async def test_enqueue_reconciliation(monkeypatch):
    job_id = uuid4()
    monkeypatch.setattr(
        execution,
        "create_and_enqueue_job",
        AsyncMock(return_value={"id": job_id, "status": "pending"}),
    )
    app = FastAPI()
    app.dependency_overrides[get_db] = _fake_db_session
    app.include_router(execution.router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/execution/reconciliation/enqueue")
    assert response.status_code == 202
    assert response.json()["job_id"] == str(job_id)


@pytest.mark.asyncio
async def test_portfolio_without_alpaca_returns_503():
    from config import get_settings

    get_settings.cache_clear()
    app = FastAPI()
    app.include_router(execution.router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/execution/portfolio")
    get_settings.cache_clear()
    assert response.status_code == 503
