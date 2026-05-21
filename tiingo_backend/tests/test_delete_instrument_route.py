from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_delete_instrument_returns_204():
    with patch(
        "routes.instruments.instrument_dal.delete_instrument",
        new=AsyncMock(return_value=True),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete("/api/v1/instruments/AAPL")

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_instrument_returns_404_when_missing():
    with patch(
        "routes.instruments.instrument_dal.delete_instrument",
        new=AsyncMock(return_value=False),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete("/api/v1/instruments/UNKNOWN")

    assert resp.status_code == 404
