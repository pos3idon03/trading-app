from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from features.market_data.overview_macro import (
    _change_from_offset,
    _ma_position,
    _ytd_change,
)
from main import app


def _obs(day: int, value: float) -> dict:
    return {"obs_date": date(2024, 1, day), "value": value}


def test_change_from_offset():
    obs = [_obs(1, 100.0), _obs(2, 110.0)]
    assert _change_from_offset(obs, 1) == 10.0


def test_ytd_change():
    obs = [
        {"obs_date": date(2024, 1, 15), "value": 100.0},
        {"obs_date": date(2024, 6, 1), "value": 120.0},
    ]
    assert _ytd_change(obs) == 20.0


def test_ma_position_above_below():
    obs = [{"obs_date": date(2024, 1, i), "value": float(i)} for i in range(1, 52)]
    assert _ma_position(obs, 50) == "Above"


@pytest.mark.asyncio
async def test_get_asset_overview_stocks():
    payload = {
        "asset_type": "stock",
        "as_of": datetime(2024, 6, 1, tzinfo=timezone.utc),
        "rows": [{
            "symbol": "AAPL",
            "name": "Apple",
            "as_of": datetime(2024, 6, 1, tzinfo=timezone.utc),
            "pe_ratio": 25.0,
            "dividend_yield": 1.2,
            "debt_equity": 1.5,
            "current_ratio": 1.1,
            "eps_ttm": 6.0,
            "revenue_growth": {
                "latest_period": "2024-Q1",
                "yoy": 10.0,
                "qoq": 5.0,
                "cagr": 12.5,
            },
            "ebitda_growth": {
                "latest_period": "2024-Q1",
                "yoy": 8.0,
                "qoq": 4.0,
                "cagr": 9.0,
            },
            "ocf_growth": {
                "latest_period": "2024-Q1",
                "yoy": 6.0,
                "qoq": 3.0,
                "cagr": 7.0,
            },
            "price_change_6m": 12.5,
        }],
    }

    with patch(
        "routes.overview.load_asset_overview",
        new=AsyncMock(return_value=payload),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/market-data/overview/assets", params={"asset_type": "stock"})

    assert resp.status_code == 200
    data = resp.json()
    row = data["rows"][0]
    assert row["symbol"] == "AAPL"
    assert row["revenue_growth"]["yoy"] == 10.0
    assert row["revenue_growth"]["qoq"] == 5.0
    assert row["revenue_growth"]["cagr"] == 12.5
    assert row["ebitda_growth"]["yoy"] == 8.0
    assert row["ocf_growth"]["qoq"] == 3.0


@pytest.mark.asyncio
async def test_get_asset_overview_invalid_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/market-data/overview/assets", params={"asset_type": "bond"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_macro_overview():
    payload = {
        "category": "inflation",
        "as_of": date(2024, 6, 1),
        "rows": [{
            "series_id": "CPIAUCSL",
            "title": "CPI All Urban Consumers",
            "category": "inflation",
            "frequency": "Monthly",
            "change_1m": 0.3,
            "change_3m": 1.1,
            "change_6m": 2.0,
            "change_ytd": 2.5,
            "ma50_position": "Above",
            "ma200_position": "Below",
        }],
    }

    with patch(
        "routes.overview.load_macro_overview",
        new=AsyncMock(return_value=payload),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/market-data/overview/macro", params={"category": "inflation"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["rows"][0]["series_id"] == "CPIAUCSL"
    assert data["rows"][0]["ma50_position"] == "Above"
