from features.tiingo.entitlement import DOW_30_SYMBOLS, is_fundamentals_entitled


def test_dow30_entitled():
    assert is_fundamentals_entitled("AAPL", "dow30") is True
    assert is_fundamentals_entitled("TSLA", "dow30") is False


def test_addon_entitled():
    assert is_fundamentals_entitled("TSLA", "addon_10y") is True


def test_dow30_count():
    assert len(DOW_30_SYMBOLS) == 30
