from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_fundamentals_coverage_empty():
    with patch(
        "routes.fundamentals_read.fundamentals_dal.list_fundamentals_coverage",
        new=AsyncMock(return_value=[]),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ingestion/fundamentals/coverage")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_fundamentals_coverage_returns_items():
    t1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
    t3 = datetime(2025, 5, 21, 12, 0, tzinfo=timezone.utc)
    coverage = [
        {
            "symbol": "MSFT",
            "name": "Microsoft",
            "metric_count": 100,
            "first_report_date": t1,
            "latest_report_date": t2,
            "last_ingested_at": t3,
        },
        {
            "symbol": "AAPL",
            "name": "Apple",
            "metric_count": 80,
            "first_report_date": t1,
            "latest_report_date": t2,
            "last_ingested_at": t2,
        },
    ]

    with patch(
        "routes.fundamentals_read.fundamentals_dal.list_fundamentals_coverage",
        new=AsyncMock(return_value=coverage),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ingestion/fundamentals/coverage")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["items"][0]["symbol"] == "MSFT"
    assert data["items"][0]["metric_count"] == 100
    assert "last_ingested_at" in data["items"][0]
