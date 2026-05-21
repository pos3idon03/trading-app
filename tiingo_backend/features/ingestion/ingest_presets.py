from dtos.market_data_dto import OHLCVBackfillRequest

FULL_OHLCV_TIMEFRAMES = ["1d", "1m", "5m", "15m", "30m", "1h"]
FULL_OHLCV_SOURCES = ["tiingo_eod", "tiingo_iex", "tiingo_crypto"]


def ohlcv_backfill_request(symbols: list[str]) -> OHLCVBackfillRequest:
    return OHLCVBackfillRequest(
        symbols=symbols,
        timeframes=list(FULL_OHLCV_TIMEFRAMES),
        sources=list(FULL_OHLCV_SOURCES),
    )
