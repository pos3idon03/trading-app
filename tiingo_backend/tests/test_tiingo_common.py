import pytest

from features.tiingo.common import parse_timestamp, resample_freq, symbol_to_crypto_ticker


def test_parse_timestamp_z():
    ts = parse_timestamp("2024-01-15T10:00:00Z")
    assert ts.year == 2024


def test_resample_freq():
    assert resample_freq("5m") == "5min"


def test_crypto_ticker():
    assert symbol_to_crypto_ticker("BTC-USD") == "btcusd"


def test_crypto_ticker_invalid():
    with pytest.raises(ValueError):
        symbol_to_crypto_ticker("BTCUSD")
