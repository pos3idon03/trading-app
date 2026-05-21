from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_macro_observations_order_asc():
    observations = [
        {"obs_date": date(2024, 1, 1), "value": 1.0},
        {"obs_date": date(2024, 2, 1), "value": 2.0},
    ]

    with patch(
        "routes.macro.macro_dal.get_observations",
        new=AsyncMock(return_value=observations),
    ) as mock_get:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ingestion/macro/observations/GDP?order=asc")

    assert resp.status_code == 200
    mock_get.assert_awaited_once()
    call_kwargs = mock_get.await_args.kwargs
    assert call_kwargs["order"] == "asc"
    assert call_kwargs["start"] is None
    assert call_kwargs["end"] is None


@pytest.mark.asyncio
async def test_macro_observations_invalid_order():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/ingestion/macro/observations/GDP?order=invalid")

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_macro_observations_date_range():
    observations = [{"obs_date": date(2024, 6, 1), "value": 3.0}]

    with patch(
        "routes.macro.macro_dal.get_observations",
        new=AsyncMock(return_value=observations),
    ) as mock_get:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/ingestion/macro/observations/GDP"
                "?start=2024-01-01&end=2024-12-31&order=asc"
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    mock_get.assert_awaited_once()
    call_kwargs = mock_get.await_args.kwargs
    assert call_kwargs["start"] == date(2024, 1, 1)
    assert call_kwargs["end"] == date(2024, 12, 31)


@pytest.mark.asyncio
async def test_macro_observations_invalid_date_range():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/ingestion/macro/observations/GDP"
            "?start=2024-12-31&end=2024-01-01"
        )

    assert resp.status_code == 400
    assert "start must be before" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_macro_observations_all_returns_unlimited():
    observations = [
        {"obs_date": date(1962, 1, 1), "value": 1.0},
        {"obs_date": date(2024, 5, 1), "value": 4.5},
    ]

    with patch(
        "routes.macro.macro_dal.get_observations",
        new=AsyncMock(return_value=observations),
    ) as mock_get:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/ingestion/macro/observations/DGS10?all=true&order=asc"
            )

    assert resp.status_code == 200
    assert resp.json()["count"] == 2
    mock_get.assert_awaited_once()
    positional_limit = mock_get.await_args.args[2]
    assert positional_limit is None
