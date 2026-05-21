from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


def _period_row(period: str, total: float | None, price: float | None = None, div: float | None = None):
    return {
        "period": period,
        "price_change_pct": price if price is not None else total,
        "dividend_return_pct": div if div is not None else 0.0,
        "total_return_pct": total,
        "change_pct": total,
        "example_investment": 100,
        "example_outcome": 100 + total if total is not None else None,
        "example_dividend_income": div if div is not None else 0.0,
    }


@pytest.mark.asyncio
async def test_get_performance_success():
    instrument = {"id": 1, "symbol": "AAPL", "currency": "USD"}
    periods = [
        _period_row("1W", 2.5, price=2.0, div=0.5),
        _period_row("1M", 5.0),
        _period_row("3M", None),
        _period_row("6M", 10.0),
        _period_row("YTD", 12.0),
        _period_row("1Y", 20.0),
        _period_row("2Y", 30.0),
        _period_row("5Y", 50.0),
    ]
    as_of = datetime(2024, 6, 1, tzinfo=timezone.utc)

    with (
        patch("routes.market_data.instrument_dal.get_by_symbol", new=AsyncMock(return_value=instrument)),
        patch(
            "routes.market_data.load_performance",
            new=AsyncMock(return_value=(periods, as_of)),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/market-data/performance/AAPL")

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["currency"] == "USD"
    assert len(data["periods"]) == 8
    assert data["periods"][0]["period"] == "1W"
    assert data["periods"][0]["change_pct"] == 2.5
    assert data["periods"][0]["price_change_pct"] == 2.0
    assert data["periods"][0]["dividend_return_pct"] == 0.5
    assert data["periods"][0]["total_return_pct"] == 2.5


@pytest.mark.asyncio
async def test_get_kpis_success():
    from features.market_data.stock_kpis import KpiItem

    instrument = {"id": 1, "symbol": "AAPL"}
    as_of = datetime(2024, 6, 1, tzinfo=timezone.utc)
    kpis = [KpiItem(key="pe_ratio", label="P/E Ratio", value=25.0, format="ratio")]

    with (
        patch("routes.market_data.instrument_dal.get_by_symbol", new=AsyncMock(return_value=instrument)),
        patch(
            "routes.market_data.load_stock_kpis",
            new=AsyncMock(return_value=(150.0, as_of, kpis)),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/market-data/kpis/AAPL")

    assert resp.status_code == 200
    data = resp.json()
    assert data["price"] == 150.0
    assert data["kpis"][0]["key"] == "pe_ratio"
