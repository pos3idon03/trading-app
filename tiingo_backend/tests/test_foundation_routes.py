import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from routes import backtest_foundation


@pytest.mark.asyncio
async def test_list_models_disabled_returns_503(monkeypatch):
    monkeypatch.setenv("FOUNDATION_MODELS_ENABLED", "false")
    from config import get_settings

    get_settings.cache_clear()

    app = FastAPI()
    app.include_router(backtest_foundation.router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/backtest/foundation/models")
    assert response.status_code == 503
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_list_models_enabled_without_torch_returns_catalog(monkeypatch):
    monkeypatch.setenv("FOUNDATION_MODELS_ENABLED", "true")
    from config import get_settings

    get_settings.cache_clear()

    app = FastAPI()
    app.include_router(backtest_foundation.router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/backtest/foundation/models")
    get_settings.cache_clear()
    assert response.status_code == 200
    data = response.json()
    ids = {item["id"] for item in data["models"]}
    assert "foundation_timesfm_2_5" in ids
    assert "foundation_chronos_2" in ids
