from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_db_instrument_search():
    instruments = [
        {
            "id": 1,
            "symbol": "AAPL",
            "name": "Apple Inc",
            "asset_type": "stock",
            "exchange": "NASDAQ",
            "currency": "USD",
            "is_active": True,
            "tiingo_ticker": "AAPL",
            "metadata": None,
        }
    ]

    with patch(
        "routes.instruments.instrument_dal.search_instruments",
        new=AsyncMock(return_value=instruments),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/instruments/db-search?query=AAPL")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_macro_series_ingested_only():
    series = [
        {
            "series_id": "GDP",
            "title": "Gross Domestic Product",
            "frequency": "Q",
            "category": "general",
            "is_enabled": True,
        }
    ]

    with patch(
        "routes.macro.macro_dal.list_ingested_series",
        new=AsyncMock(return_value=series),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ingestion/macro/series?ingested_only=true")

    assert resp.status_code == 200
    assert resp.json()[0]["series_id"] == "GDP"
