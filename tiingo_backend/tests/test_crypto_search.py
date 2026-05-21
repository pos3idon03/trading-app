from features.tiingo.crypto_search import search_crypto_meta

_SAMPLE_META = [
    {
        "ticker": "btcusd",
        "name": "Bitcoin Tether (BTC/USD)",
        "baseCurrency": "btc",
        "quoteCurrency": "usd",
    },
    {
        "ticker": "btceur",
        "name": "Bitcoin EUR",
        "baseCurrency": "btc",
        "quoteCurrency": "eur",
    },
    {
        "ticker": "ethusd",
        "name": "Ethereum Tether (ETH/USD)",
        "baseCurrency": "eth",
        "quoteCurrency": "usd",
    },
    {
        "ticker": "wbtcusd",
        "name": "Wrapped BTC USD",
        "baseCurrency": "wbtc",
        "quoteCurrency": "usd",
    },
]


def test_btc_query_ranks_btcusd_first():
    results = search_crypto_meta("BTC", _SAMPLE_META, limit=3)
    assert len(results) >= 2
    assert results[0].symbol == "BTC-USD"
    assert results[0].asset_type == "crypto"
    assert results[0].tiingo_ticker == "btcusd"


def test_btcusd_exact_ticker_match():
    results = search_crypto_meta("btcusd", _SAMPLE_META, limit=1)
    assert len(results) == 1
    assert results[0].symbol == "BTC-USD"


def test_eth_query_returns_ethusd():
    results = search_crypto_meta("ETH", _SAMPLE_META, limit=2)
    assert results[0].symbol == "ETH-USD"


def test_empty_query_returns_empty():
    assert search_crypto_meta("", _SAMPLE_META, limit=5) == []
