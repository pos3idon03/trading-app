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
async def test_resolve_best_source_prefers_alpaca_for_intraday_when_available():
    session = AsyncMock()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            ohlcv_dal,
            "get_coverage",
            AsyncMock(return_value=[
                {"source": "tiingo_crypto"},
                {"source": "alpaca_crypto"},
            ]),
        )
        source = await ohlcv_dal.resolve_best_source(session, 1, "1h")

    assert source == "alpaca_crypto"


@pytest.mark.asyncio
async def test_resolve_best_source_prefers_crypto_for_daily_when_available():
    session = AsyncMock()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            ohlcv_dal,
            "get_coverage",
            AsyncMock(return_value=[
                {"source": "tiingo_eod"},
                {"source": "tiingo_crypto"},
            ]),
        )
        source = await ohlcv_dal.resolve_best_source(session, 1, "1d")

    assert source == "tiingo_crypto"


@pytest.mark.asyncio
async def test_resolve_best_source_prefers_eod_for_daily_without_crypto():
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
    weekly = ohlcv_dal.default_start_for_timeframe("1w")
    now = datetime.now(timezone.utc)
    assert (now - daily).days >= 364 * 29
    assert (now - intraday).days >= 4
    assert (now - weekly).days >= 364 * 4


@pytest.mark.asyncio
async def test_get_bars_fetch_tail_returns_oldest_to_newest():
    t1 = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [_make_bar(t2, "tiingo_iex"), _make_bar(t1, "tiingo_iex")]
    session.execute.return_value = result_mock

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ohlcv_dal, "resolve_best_source", AsyncMock(return_value="tiingo_iex"))
        bars, _ = await ohlcv_dal.get_bars(session, 1, "5m", fetch_tail=True, limit=2)

    assert bars[0]["time"] == t1
    assert bars[1]["time"] == t2


@pytest.mark.asyncio
async def test_get_bars_dedupes_duplicate_daily_timestamps():
    day = datetime(2024, 1, 2, tzinfo=timezone.utc)
    later = datetime(2024, 1, 2, 14, 0, tzinfo=timezone.utc)
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [
        _make_bar(day),
        _make_bar(later, "tiingo_eod"),
    ]
    session.execute.return_value = result_mock

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ohlcv_dal, "resolve_best_source", AsyncMock(return_value="tiingo_eod"))
        bars, _ = await ohlcv_dal.get_bars(session, 1, "1d", limit=10)

    assert len(bars) == 1
    assert bars[0]["time"] == later


@pytest.mark.asyncio
async def test_get_bars_with_resample_returns_native_when_present():
    t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    native_bars = [{"time": t1, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "source": "tiingo_iex"}]
    session = AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ohlcv_dal, "get_bars", AsyncMock(return_value=(native_bars, "tiingo_iex")))
        mock_resample = AsyncMock()
        mp.setattr("dal.ohlcv_dal.get_resampled_bars", mock_resample)
        bars, source = await ohlcv_dal.get_bars_with_resample(session, 1, "1h")

    assert bars == native_bars
    assert source == "tiingo_iex"
    mock_resample.assert_not_called()


@pytest.mark.asyncio
async def test_get_bars_with_resample_falls_back_when_native_empty():
    t1 = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
    resampled = [{"time": t1, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "source": "tiingo_iex"}]
    session = AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ohlcv_dal, "get_bars", AsyncMock(return_value=([], None)))
        mp.setattr(ohlcv_dal, "resolve_best_source", AsyncMock(return_value="tiingo_iex"))
        mp.setattr("dal.ohlcv_dal.get_resampled_bars", AsyncMock(return_value=resampled))
        bars, source = await ohlcv_dal.get_bars_with_resample(session, 1, "1h")

    assert bars == resampled
    assert source == "tiingo_iex"


@pytest.mark.asyncio
async def test_get_bars_with_resample_4h_tries_1h_before_1m():
    t1 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    resampled = [{"time": t1, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "source": "tiingo_iex"}]
    session = AsyncMock()
    resample_mock = AsyncMock(return_value=resampled)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ohlcv_dal, "get_bars", AsyncMock(return_value=([], None)))
        mp.setattr(ohlcv_dal, "resolve_best_source", AsyncMock(return_value="tiingo_iex"))
        mp.setattr("dal.ohlcv_dal.get_resampled_bars", resample_mock)
        bars, source = await ohlcv_dal.get_bars_with_resample(session, 1, "4h")

    assert bars == resampled
    assert source == "tiingo_iex"
    assert resample_mock.await_args.args[3] == "1h"


@pytest.mark.asyncio
async def test_get_bars_with_resample_1w_uses_daily_source():
    t1 = datetime(2024, 1, 5, tzinfo=timezone.utc)
    resampled = [{"time": t1, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "source": "tiingo_eod"}]
    session = AsyncMock()
    resample_mock = AsyncMock(return_value=resampled)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ohlcv_dal, "get_bars", AsyncMock(return_value=([], None)))
        mp.setattr(ohlcv_dal, "resolve_best_source", AsyncMock(return_value="tiingo_eod"))
        mp.setattr("dal.ohlcv_dal.get_resampled_bars", resample_mock)
        bars, source = await ohlcv_dal.get_bars_with_resample(session, 1, "1w")

    assert bars == resampled
    assert source == "tiingo_eod"
    assert resample_mock.await_args.args[3] == "1d"
