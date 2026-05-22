from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from features.backtesting.bar_loader import load_multi_timeframe_bars


@pytest.mark.asyncio
async def test_load_multi_timeframe_applies_warmup_for_signal_tf():
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    end = datetime(2024, 6, 30, tzinfo=timezone.utc)
    session = AsyncMock()
    captured_starts: dict[str, datetime] = {}

    async def fake_get_bars(_session, _iid, timeframe, **kwargs):
        captured_starts[timeframe] = kwargs["start"]
        return [{"time": kwargs["start"], "open": 1, "high": 1, "low": 1, "close": 1, "volume": 0}], "tiingo_iex"

    with patch(
        "features.backtesting.bar_loader.ohlcv_dal.get_bars_with_resample",
        new=AsyncMock(side_effect=fake_get_bars),
    ):
        await load_multi_timeframe_bars(
            session,
            1,
            {"15m", "4h"},
            start,
            end,
            decision_timeframe="15m",
            warmup_bars_by_tf={"4h": 26},
        )

    assert captured_starts["15m"] == start
    assert captured_starts["4h"] < start
