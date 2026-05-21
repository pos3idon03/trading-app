from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from dal import ohlcv_dal
from models.market_data import OHLCV


def _make_bar(time: datetime, source: str = "tiingo_eod") -> MagicMock:
    row = MagicMock(spec=OHLCV)
    row.time = time
    row.open = 100.0
    row.high = 105.0
    row.low = 99.0
    row.close = 102.0
    row.volume = 1000
    row.source = source
    return row


@pytest.mark.asyncio
async def test_get_bars_orders_ascending():
    t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2024, 1, 2, tzinfo=timezone.utc)
    session = AsyncMock()

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [
        _make_bar(t1),
        _make_bar(t2),
    ]
    session.execute.return_value = result_mock

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            ohlcv_dal,
            "resolve_best_source",
            AsyncMock(return_value="tiingo_eod"),
        )
        bars, source = await ohlcv_dal.get_bars(session, 1, "1d")

    assert source == "tiingo_eod"
    assert len(bars) == 2
    assert bars[0]["time"] == t1
    assert bars[1]["close"] == 102.0


@pytest.mark.asyncio
async def test_get_bars_returns_empty_when_no_source():
    session = AsyncMock()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            ohlcv_dal,
            "resolve_best_source",
            AsyncMock(return_value=None),
        )
        bars, source = await ohlcv_dal.get_bars(session, 1, "1d")

    assert bars == []
    assert source is None


@pytest.mark.asyncio
async def test_resolve_best_source_prefers_eod_for_daily():
    session = AsyncMock()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            ohlcv_dal,
            "get_coverage",
            AsyncMock(return_value=[
                {"source": "tiingo_iex"},
                {"source": "tiingo_eod"},
            ]),
        )
        source = await ohlcv_dal.resolve_best_source(session, 1, "1d")

    assert source == "tiingo_eod"


@pytest.mark.asyncio
async def test_default_start_for_timeframe():
    daily = ohlcv_dal.default_start_for_timeframe("1d")
    intraday = ohlcv_dal.default_start_for_timeframe("5m")
    now = datetime.now(timezone.utc)
    assert (now - daily).days >= 364
    assert (now - intraday).days >= 4
