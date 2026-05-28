from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from routes import execution


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
