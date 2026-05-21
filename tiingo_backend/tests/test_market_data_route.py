from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_get_ohlcv_by_symbol_success():
    instrument = {"id": 1, "symbol": "AAPL"}
    bars = [
        {
            "time": datetime(2024, 6, 1, tzinfo=timezone.utc),
            "open": 190.0,
            "high": 195.0,
            "low": 189.0,
            "close": 194.0,
            "volume": 5000,
            "source": "tiingo_eod",
        }
    ]

    with (
        patch("routes.market_data.instrument_dal.get_by_symbol", new=AsyncMock(return_value=instrument)),
        patch("routes.market_data.ohlcv_dal.get_bars", new=AsyncMock(return_value=(bars, "tiingo_eod"))),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/market-data/ohlcv/AAPL?timeframe=1d")

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["count"] == 1
    assert data["records"][0]["close"] == 194.0


@pytest.mark.asyncio
async def test_get_ohlcv_instrument_not_found():
    with patch(
        "routes.market_data.instrument_dal.get_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/market-data/ohlcv/FAKE")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_ohlcv_no_data():
    instrument = {"id": 1, "symbol": "EMPTY"}

    with (
        patch("routes.market_data.instrument_dal.get_by_symbol", new=AsyncMock(return_value=instrument)),
        patch("routes.market_data.ohlcv_dal.get_bars", new=AsyncMock(return_value=([], None))),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/market-data/ohlcv/EMPTY?timeframe=1d")

    assert resp.status_code == 404
