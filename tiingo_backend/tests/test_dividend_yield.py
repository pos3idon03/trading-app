from unittest.mock import AsyncMock, patch

import pytest

from features.market_data.dividend_yield import resolve_dividend_yield


@pytest.mark.asyncio
async def test_resolve_dividend_yield_skips_api_when_disabled():
    session = AsyncMock()
    with patch(
        "features.market_data.dividend_yield.check_and_increment",
        new=AsyncMock(),
    ) as mock_rate, patch(
        "features.market_data.dividend_yield.distributions_client.fetch_distribution_yield",
        new=AsyncMock(return_value=1.85),
    ) as mock_api, patch(
        "features.market_data.dividend_yield._div_cash_yield",
        new=AsyncMock(return_value=0.72),
    ) as mock_fallback:
        result = await resolve_dividend_yield(
            session,
            instrument_id=4,
            symbol="MSFT",
            use_api=False,
        )

    assert result == 0.72
    mock_rate.assert_not_awaited()
    mock_api.assert_not_awaited()
    mock_fallback.assert_awaited_once_with(session, 4)


@pytest.mark.asyncio
async def test_resolve_dividend_yield_prefers_api_value():
    session = AsyncMock()
    with patch(
        "features.market_data.dividend_yield.check_and_increment",
        new=AsyncMock(),
    ), patch(
        "features.market_data.dividend_yield.distributions_client.fetch_distribution_yield",
        new=AsyncMock(return_value=1.85),
    ) as mock_api, patch(
        "features.market_data.dividend_yield._div_cash_yield",
        new=AsyncMock(return_value=0.5),
    ) as mock_fallback:
        result = await resolve_dividend_yield(
            session,
            instrument_id=1,
            symbol="QQQ",
            tiingo_ticker="QQQ",
        )

    assert result == 1.85
    mock_api.assert_awaited_once_with("QQQ")
    mock_fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_dividend_yield_falls_back_to_div_cash():
    session = AsyncMock()
    with patch(
        "features.market_data.dividend_yield.check_and_increment",
        new=AsyncMock(),
    ), patch(
        "features.market_data.dividend_yield.distributions_client.fetch_distribution_yield",
        new=AsyncMock(return_value=None),
    ), patch(
        "features.market_data.dividend_yield._div_cash_yield",
        new=AsyncMock(return_value=0.72),
    ) as mock_fallback:
        result = await resolve_dividend_yield(
            session,
            instrument_id=2,
            symbol="DIV",
            tiingo_ticker="DIV",
        )

    assert result == 0.72
    mock_fallback.assert_awaited_once_with(session, 2)


@pytest.mark.asyncio
async def test_resolve_dividend_yield_falls_back_when_api_raises():
    session = AsyncMock()
    with patch(
        "features.market_data.dividend_yield.check_and_increment",
        new=AsyncMock(),
    ), patch(
        "features.market_data.dividend_yield.distributions_client.fetch_distribution_yield",
        new=AsyncMock(side_effect=RuntimeError("api down")),
    ), patch(
        "features.market_data.dividend_yield._div_cash_yield",
        new=AsyncMock(return_value=0.9),
    ) as mock_fallback:
        result = await resolve_dividend_yield(
            session,
            instrument_id=3,
            symbol="SPY",
        )

    assert result == 0.9
    mock_fallback.assert_awaited_once_with(session, 3)
