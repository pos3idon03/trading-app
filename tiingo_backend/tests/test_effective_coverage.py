from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from features.market_data.effective_coverage import get_effective_coverage


@pytest.mark.asyncio
async def test_effective_coverage_returns_native_when_present():
    native = [
        {
            "source": "tiingo_iex",
            "min_time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "max_time": datetime(2024, 3, 1, tzinfo=timezone.utc),
            "bar_count": 120,
        },
    ]
    session = AsyncMock()

    with patch(
        "features.market_data.effective_coverage.ohlcv_dal.get_coverage",
        new=AsyncMock(return_value=native),
    ):
        result = await get_effective_coverage(session, 1, "4h")

    assert result["effective"]["bar_count"] == 120
    assert result["effective"]["derived_from"] is None


@pytest.mark.asyncio
async def test_effective_coverage_derives_from_1h_when_no_native_4h():
    session = AsyncMock()
    hourly_cov = [
        {
            "source": "tiingo_iex",
            "min_time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "max_time": datetime(2024, 3, 1, tzinfo=timezone.utc),
            "bar_count": 400,
        },
    ]
    bars = [
        {"time": datetime(2024, 1, 1, 12, tzinfo=timezone.utc), "open": 1, "high": 1, "low": 1, "close": 1, "volume": 0},
    ]

    with patch(
        "features.market_data.effective_coverage.ohlcv_dal.get_coverage",
        new=AsyncMock(side_effect=[[], hourly_cov]),
    ), patch(
        "features.market_data.effective_coverage.ohlcv_dal.get_bars_with_resample",
        new=AsyncMock(return_value=(bars, "tiingo_iex")),
    ):
        result = await get_effective_coverage(session, 1, "4h")

    assert result["effective"]["derived_from"] == "1h"
    assert result["effective"]["bar_count"] == 1
