from datetime import datetime, timezone

from dtos.market_data_dto import OHLCVRecord
from features.market_data.bar_aggregate import aggregate_ohlcv_bars


def _bar(hour: int, close: float) -> OHLCVRecord:
    return OHLCVRecord(
        time=datetime(2024, 1, 1, hour, tzinfo=timezone.utc),
        instrument_id=1,
        timeframe="1h",
        open=close - 1,
        high=close + 1,
        low=close - 2,
        close=close,
        volume=10,
        source="tiingo_crypto",
    )


def test_aggregate_4h_from_hourly():
    records = [_bar(0, 100), _bar(1, 101), _bar(2, 102), _bar(3, 103)]
    result = aggregate_ohlcv_bars(records, "4h")
    assert len(result) == 1
    assert result[0].timeframe == "4h"
    assert result[0].open == 99
    assert result[0].close == 103
    assert result[0].volume == 40


def test_aggregate_unknown_timeframe_returns_input():
    records = [_bar(0, 100)]
    assert aggregate_ohlcv_bars(records, "1h") == records
