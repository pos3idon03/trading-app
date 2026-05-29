from features.execution.alpaca_symbols import (
    execution_asset_type,
    from_alpaca_symbol,
    to_alpaca_symbol,
)


def test_to_alpaca_crypto_symbol():
    assert to_alpaca_symbol("BTC-USD", "crypto") == "BTC/USD"


def test_to_alpaca_equity_symbol():
    assert to_alpaca_symbol("aapl", "stock") == "AAPL"


def test_from_alpaca_crypto_symbol():
    assert from_alpaca_symbol("BTC/USD") == "BTC-USD"


def test_from_alpaca_concatenated_crypto_symbol():
    assert from_alpaca_symbol("BTCUSD") == "BTC-USD"


def test_execution_asset_type_normalizes():
    assert execution_asset_type("crypto") == "crypto"
    assert execution_asset_type("equity") == "stock"
