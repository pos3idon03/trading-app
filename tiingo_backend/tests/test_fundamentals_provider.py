from unittest.mock import AsyncMock, patch

import pytest

from features.market_data.fundamentals_provider import fetch_fundamentals_rows


def _row(source: str) -> dict:
    return {
        "time": "2024-03-31T00:00:00+00:00",
        "metric_name": "revenue",
        "value": 1.0,
        "period": "2024-Q1",
        "statement_type": "incomeStatement",
        "source": source,
        "raw_data": {},
    }


@pytest.mark.asyncio
async def test_fetch_fundamentals_rows_uses_tiingo_when_data_present():
    session = AsyncMock()
    with (
        patch(
            "features.market_data.fundamentals_provider.is_fundamentals_entitled",
            return_value=True,
        ),
        patch(
            "features.market_data.fundamentals_provider._fetch_tiingo_rows",
            new=AsyncMock(return_value=[_row("tiingo")]),
        ) as mock_tiingo,
        patch(
            "features.market_data.fundamentals_provider._fetch_yfinance_rows",
            new=AsyncMock(return_value=[_row("yfinance")]),
        ) as mock_yfinance,
    ):
        rows = await fetch_fundamentals_rows("AAPL", asset_type="stock", session=session)

    assert rows[0]["source"] == "tiingo"
    mock_tiingo.assert_awaited_once()
    mock_yfinance.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_fundamentals_rows_falls_back_to_yfinance_when_tiingo_empty():
    session = AsyncMock()
    with (
        patch(
            "features.market_data.fundamentals_provider.is_fundamentals_entitled",
            return_value=True,
        ),
        patch(
            "features.market_data.fundamentals_provider._fetch_tiingo_rows",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "features.market_data.fundamentals_provider._fetch_yfinance_rows",
            new=AsyncMock(return_value=[_row("yfinance")]),
        ) as mock_yfinance,
    ):
        rows = await fetch_fundamentals_rows("NVDA", asset_type="stock", session=session)

    assert rows[0]["source"] == "yfinance"
    mock_yfinance.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_fundamentals_rows_not_entitled_skips_tiingo():
    session = AsyncMock()
    with (
        patch(
            "features.market_data.fundamentals_provider.is_fundamentals_entitled",
            return_value=False,
        ),
        patch(
            "features.market_data.fundamentals_provider._fetch_tiingo_rows",
            new=AsyncMock(return_value=[_row("tiingo")]),
        ) as mock_tiingo,
        patch(
            "features.market_data.fundamentals_provider._fetch_yfinance_rows",
            new=AsyncMock(return_value=[_row("yfinance")]),
        ) as mock_yfinance,
    ):
        rows = await fetch_fundamentals_rows("NVDA", asset_type="stock", session=session)

    assert rows[0]["source"] == "yfinance"
    mock_tiingo.assert_not_awaited()
    mock_yfinance.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_fundamentals_rows_non_stock_returns_empty():
    session = AsyncMock()
    rows = await fetch_fundamentals_rows("BTCUSD", asset_type="crypto", session=session)
    assert rows == []
