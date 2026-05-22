from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from features.market_data.overview_assets import _build_price_row, load_asset_overview


@pytest.mark.asyncio
async def test_build_price_row_uses_distribution_yield():
    instrument = {"id": 10, "symbol": "QQQ", "name": "Invesco QQQ", "tiingo_ticker": "QQQ"}
    bars = [{"time": datetime(2024, 6, 1, tzinfo=timezone.utc), "close": 450.0, "div_cash": 0}]
    session = AsyncMock()

    with patch(
        "features.market_data.overview_assets._load_bars",
        new=AsyncMock(return_value=bars),
    ), patch(
        "features.market_data.overview_assets._period_map",
        return_value={"1M": 2.5, "1Y": 12.0},
    ), patch(
        "features.market_data.overview_assets.resolve_dividend_yield",
        new=AsyncMock(return_value=0.55),
    ) as mock_yield:
        row = await _build_price_row(session, instrument)

    assert row["dividend_yield"] == 0.55
    mock_yield.assert_awaited_once_with(
        session,
        10,
        symbol="QQQ",
        tiingo_ticker="QQQ",
    )


@pytest.mark.asyncio
async def test_load_asset_overview_etf_rows_include_dividend_yield():
    instruments = [
        {"id": 1, "symbol": "QQQ", "name": "Invesco QQQ", "tiingo_ticker": "QQQ", "asset_type": "etf"},
    ]
    session = AsyncMock()

    async def fake_price_row(sess, instrument):
        return {
            "symbol": instrument["symbol"],
            "name": instrument["name"],
            "as_of": datetime(2024, 6, 1, tzinfo=timezone.utc),
            "dividend_yield": 0.55,
            "performance": {"1M": 2.5},
        }

    with patch(
        "features.market_data.overview_assets.instrument_dal.list_instruments",
        new=AsyncMock(return_value=instruments),
    ), patch(
        "features.market_data.overview_assets._build_price_row",
        new=AsyncMock(side_effect=fake_price_row),
    ):
        payload = await load_asset_overview(session, "etf")

    assert payload["asset_type"] == "etf"
    assert payload["rows"][0]["dividend_yield"] == 0.55
