"""Tests for features.execution.symbol_resolver.to_alpaca_symbol."""
import pytest

from features.execution.symbol_resolver import canonical_alpaca_symbol, to_alpaca_symbol


class TestCanonicalAlpacaSymbol:
    def test_btcusd_compact(self):
        assert canonical_alpaca_symbol("BTCUSD") == "BTC/USD"

    def test_ethusdt_compact(self):
        assert canonical_alpaca_symbol("ETHUSDT") == "ETH/USDT"

    def test_slash_form_passthrough(self):
        assert canonical_alpaca_symbol("BTC/USD") == "BTC/USD"

    def test_dash_crypto_normalized(self):
        assert canonical_alpaca_symbol("btc-usd") == "BTC/USD"

    def test_equity_unchanged(self):
        assert canonical_alpaca_symbol("AAPL") == "AAPL"


class TestCryptoSymbols:
    def test_btc_usd_converted(self):
        assert to_alpaca_symbol("BTC-USD", "crypto") == "BTC/USD"

    def test_eth_usd_converted(self):
        assert to_alpaca_symbol("ETH-USD", "crypto") == "ETH/USD"

    def test_crypto_already_normalized_passthrough(self):
        assert to_alpaca_symbol("BTC/USD", "crypto") == "BTC/USD"

    def test_crypto_no_dash_passthrough(self):
        assert to_alpaca_symbol("SOLUSDC", "crypto") == "SOLUSDC"


class TestMisclassifiedCryptoAsStock:
    """Local DB rows can have asset_type=stock for yfinance crypto tickers."""

    def test_btc_usd_treated_as_crypto_when_stock(self):
        assert to_alpaca_symbol("BTC-USD", "stock") == "BTC/USD"

    def test_eth_eur_when_stock(self):
        assert to_alpaca_symbol("ETH-EUR", "stock") == "ETH/EUR"

    def test_unknown_type_but_crypto_pair_suffix(self):
        assert to_alpaca_symbol("SOL-USD", "other") == "SOL/USD"


class TestUsEquitySymbols:
    def test_hyphenated_class_share_not_crypto(self):
        assert to_alpaca_symbol("BRK-B", "stock") == "BRK-B"

    def test_aapl_unchanged(self):
        assert to_alpaca_symbol("AAPL", "stock") == "AAPL"

    def test_msft_unchanged(self):
        assert to_alpaca_symbol("MSFT", "stock") == "MSFT"

    def test_spy_etf_unchanged(self):
        assert to_alpaca_symbol("SPY", "etf") == "SPY"

    def test_qqq_etf_unchanged(self):
        assert to_alpaca_symbol("QQQ", "etf") == "QQQ"


class TestNonUsEquitySymbols:
    def test_barc_london_returns_none(self):
        assert to_alpaca_symbol("BARC.L", "stock") is None

    def test_sap_xetra_returns_none(self):
        assert to_alpaca_symbol("SAP.DE", "stock") is None

    def test_toyota_tokyo_returns_none(self):
        assert to_alpaca_symbol("7203.T", "stock") is None

    def test_any_dot_suffix_returns_none(self):
        assert to_alpaca_symbol("ABC.PA", "stock") is None


class TestUnsupportedAssetTypes:
    def test_forex_returns_none(self):
        assert to_alpaca_symbol("EURUSD=X", "forex") is None

    def test_index_returns_none(self):
        assert to_alpaca_symbol("^GSPC", "index") is None

    def test_future_returns_none(self):
        assert to_alpaca_symbol("ES=F", "future") is None

    def test_option_returns_none(self):
        assert to_alpaca_symbol("AAPL240119C00150000", "option") is None

    def test_unknown_asset_type_returns_none(self):
        assert to_alpaca_symbol("XYZ", "unknown_type") is None


class TestEdgeCases:
    def test_empty_symbol_returns_none(self):
        assert to_alpaca_symbol("", "stock") is None

    def test_asset_type_case_insensitive(self):
        assert to_alpaca_symbol("BTC-USD", "CRYPTO") == "BTC/USD"
        assert to_alpaca_symbol("AAPL", "STOCK") == "AAPL"

    def test_none_asset_type_defaults_to_stock(self):
        assert to_alpaca_symbol("AAPL", None) == "AAPL"

    def test_empty_asset_type_defaults_to_stock(self):
        assert to_alpaca_symbol("AAPL", "") == "AAPL"
