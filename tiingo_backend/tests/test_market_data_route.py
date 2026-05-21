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
        patch("routes.market_data.ohlcv_dal.get_bars_with_resample", new=AsyncMock(return_value=(bars, "tiingo_eod"))),
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
        patch("routes.market_data.ohlcv_dal.get_bars_with_resample", new=AsyncMock(return_value=([], None))),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/market-data/ohlcv/EMPTY?timeframe=1d")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_ohlcv_invalid_timeframe():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/market-data/ohlcv/AAPL?timeframe=2h")

    assert resp.status_code == 400
    assert "Unsupported timeframe" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_ohlcv_invalid_date_range():
    instrument = {"id": 1, "symbol": "AAPL"}
    with patch(
        "routes.market_data.instrument_dal.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/market-data/ohlcv/AAPL"
                "?start=2024-06-01T00:00:00Z&end=2024-01-01T00:00:00Z"
            )

    assert resp.status_code == 400
    assert "start must be before" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_ohlcv_resample_fallback():
    instrument = {"id": 1, "symbol": "AAPL"}
    bars = [
        {
            "time": datetime(2024, 6, 1, 13, 0, tzinfo=timezone.utc),
            "open": 190.0,
            "high": 195.0,
            "low": 189.0,
            "close": 194.0,
            "volume": 5000,
            "source": "tiingo_iex",
        }
    ]

    with (
        patch("routes.market_data.instrument_dal.get_by_symbol", new=AsyncMock(return_value=instrument)),
        patch(
            "routes.market_data.ohlcv_dal.get_bars_with_resample",
            new=AsyncMock(return_value=(bars, "tiingo_iex")),
        ) as mock_resample,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/market-data/ohlcv/AAPL?timeframe=1h")

    assert resp.status_code == 200
    assert resp.json()["timeframe"] == "1h"
    mock_resample.assert_awaited_once()
    assert mock_resample.await_args.kwargs["fetch_tail"] is True


@pytest.mark.asyncio
async def test_get_ohlcv_daily_uses_full_history():
    instrument = {"id": 1, "symbol": "AAPL"}
    bars = [{"time": datetime(2016, 1, 1, tzinfo=timezone.utc), "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 1, "source": "tiingo_eod"}]

    with (
        patch("routes.market_data.instrument_dal.get_by_symbol", new=AsyncMock(return_value=instrument)),
        patch(
            "routes.market_data.ohlcv_dal.get_bars_with_resample",
            new=AsyncMock(return_value=(bars, "tiingo_eod")),
        ) as mock_resample,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/market-data/ohlcv/AAPL?timeframe=1d&limit=10000")

    assert resp.status_code == 200
    kwargs = mock_resample.await_args.kwargs
    assert kwargs["fetch_tail"] is False
    assert kwargs["start"] is not None
