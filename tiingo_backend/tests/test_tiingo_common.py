import pytest

from features.tiingo.common import (
    normalize_crypto_symbol,
    parse_timestamp,
    resample_freq,
    symbol_to_crypto_ticker,
)


def test_parse_timestamp_z():
    ts = parse_timestamp("2024-01-15T10:00:00Z")
    assert ts.year == 2024


def test_resample_freq():
    assert resample_freq("5m") == "5min"


def test_crypto_ticker_hyphenated():
    assert symbol_to_crypto_ticker("BTC-USD") == "btcusd"


def test_crypto_ticker_concatenated():
    assert symbol_to_crypto_ticker("btcusd") == "btcusd"
    assert symbol_to_crypto_ticker("BTCUSD") == "btcusd"


def test_normalize_crypto_symbol_hyphenated():
    assert normalize_crypto_symbol("btc-usd") == "BTC-USD"


def test_normalize_crypto_symbol_concatenated():
    assert normalize_crypto_symbol("btcusd") == "BTC-USD"
    assert normalize_crypto_symbol("ethusdt") == "ETH-USDT"


def test_normalize_crypto_symbol_invalid():
    with pytest.raises(ValueError):
        normalize_crypto_symbol("INVALID")
