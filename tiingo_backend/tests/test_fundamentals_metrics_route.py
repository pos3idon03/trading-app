from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app

_T1 = datetime(2024, 3, 31, tzinfo=timezone.utc)
_T2 = datetime(2024, 6, 30, tzinfo=timezone.utc)


def _metric_row(time: datetime, name: str, value: float, period: str) -> dict:
    return {
        "time": time,
        "metric_name": name,
        "value": value,
        "period": period,
        "statement_type": "incomeStatement",
    }


@pytest.mark.asyncio
async def test_fundamentals_metrics_quarterly_filters():
    rows = [_metric_row(_T1, "revenue", 100.0, "2024-Q1")]
    inst = {"id": 1, "symbol": "AAPL", "asset_type": "stock"}

    with (
        patch(
            "routes.fundamentals_read.instrument_dal.get_by_symbol",
            new=AsyncMock(return_value=inst),
        ),
        patch(
            "routes.fundamentals_read.ensure_fundamentals_in_db",
            new=AsyncMock(return_value=rows),
        ) as mock_ensure,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/ingestion/fundamentals/AAPL"
                "?period_type=quarterly&metric_names=revenue&order=asc"
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["period_type"] == "quarterly"
    assert data["count"] == 1
    mock_ensure.assert_awaited_once()
    kwargs = mock_ensure.await_args.kwargs
    assert kwargs["period_type"] == "quarterly"
    assert kwargs["metric_names"] == ["revenue"]
    assert kwargs["order"] == "asc"


@pytest.mark.asyncio
async def test_fundamentals_metrics_annual():
    rows = [_metric_row(_T2, "netinc", 50.0, "FY-2023")]
    inst = {"id": 2, "symbol": "MSFT", "asset_type": "stock"}

    with (
        patch(
            "routes.fundamentals_read.instrument_dal.get_by_symbol",
            new=AsyncMock(return_value=inst),
        ),
        patch(
            "routes.fundamentals_read.ensure_fundamentals_in_db",
            new=AsyncMock(return_value=rows),
        ) as mock_ensure,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ingestion/fundamentals/MSFT?period_type=annual")

    assert resp.status_code == 200
    assert resp.json()["period_type"] == "annual"
    assert mock_ensure.await_args.kwargs["period_type"] == "annual"


@pytest.mark.asyncio
async def test_fundamentals_metrics_invalid_period_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/ingestion/fundamentals/AAPL?period_type=monthly")

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_fundamentals_metrics_not_found_instrument():
    with patch(
        "routes.fundamentals_read.instrument_dal.get_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ingestion/fundamentals/UNKNOWN")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_fundamentals_metrics_empty_rows():
    inst = {"id": 1, "symbol": "AAPL", "asset_type": "stock"}
    with (
        patch(
            "routes.fundamentals_read.instrument_dal.get_by_symbol",
            new=AsyncMock(return_value=inst),
        ),
        patch(
            "routes.fundamentals_read.ensure_fundamentals_in_db",
            new=AsyncMock(return_value=[]),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ingestion/fundamentals/AAPL")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_fundamentals_metrics_yfinance_fallback_returns_rows():
    inst = {"id": 3, "symbol": "NVDA", "asset_type": "stock"}
    rows = [_metric_row(_T1, "revenue", 200.0, "2024-Q1")]

    with (
        patch(
            "routes.fundamentals_read.instrument_dal.get_by_symbol",
            new=AsyncMock(return_value=inst),
        ),
        patch(
            "routes.fundamentals_read.ensure_fundamentals_in_db",
            new=AsyncMock(return_value=rows),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ingestion/fundamentals/NVDA")

    assert resp.status_code == 200
    assert resp.json()["count"] == 1


@pytest.mark.asyncio
async def test_fundamentals_metrics_all_unlimited():
    inst = {"id": 1, "symbol": "AAPL", "asset_type": "stock"}
    with (
        patch(
            "routes.fundamentals_read.instrument_dal.get_by_symbol",
            new=AsyncMock(return_value=inst),
        ),
        patch(
            "routes.fundamentals_read.ensure_fundamentals_in_db",
            new=AsyncMock(return_value=[_metric_row(_T1, "eps", 1.5, "2024-Q1")]),
        ) as mock_ensure,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ingestion/fundamentals/AAPL?all=true")

    assert resp.status_code == 200
    assert mock_ensure.await_args.kwargs["limit"] is None
