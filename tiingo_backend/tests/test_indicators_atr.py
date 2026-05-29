from features.backtesting.indicators import compute_atr


def test_compute_atr_returns_values_after_warmup():
    highs = [float(10 + i) for i in range(20)]
    lows = [float(8 + i) for i in range(20)]
    closes = [float(9 + i) for i in range(20)]
    atr = compute_atr(highs, lows, closes, 14)
    assert atr[14] is not None
    assert atr[19] is not None
    assert atr[13] is None
