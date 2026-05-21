from features.ingestion.ingest_presets import (
    FULL_OHLCV_SOURCES,
    FULL_OHLCV_TIMEFRAMES,
    ohlcv_backfill_request,
)


def test_full_ohlcv_preset_includes_daily_and_intraday():
    assert "1d" in FULL_OHLCV_TIMEFRAMES
    assert "1m" in FULL_OHLCV_TIMEFRAMES
    assert "1h" in FULL_OHLCV_TIMEFRAMES


def test_ohlcv_backfill_request_for_symbol():
    req = ohlcv_backfill_request(["AAPL"])
    assert req.symbols == ["AAPL"]
    assert req.timeframes == FULL_OHLCV_TIMEFRAMES
    assert req.sources == FULL_OHLCV_SOURCES
