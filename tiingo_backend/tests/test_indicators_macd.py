from features.backtesting.indicators import compute_macd, compute_obv, compute_ichimoku


def test_macd_returns_three_series():
    closes = [float(i) for i in range(1, 40)]
    line, signal, hist = compute_macd(closes)
    assert len(line) == len(closes)
    assert any(v is not None for v in line)
    assert any(v is not None for v in signal)
    assert any(v is not None for v in hist)


def test_obv_tracks_volume_direction():
    closes = [10.0, 11.0, 10.5, 11.5]
    volumes = [100.0, 200.0, 150.0, 180.0]
    obv = compute_obv(closes, volumes)
    assert obv[1] > obv[0]
    assert obv[2] < obv[1]


def test_ichimoku_midlines():
    highs = [float(i + 1) for i in range(30)]
    lows = [float(i) for i in range(30)]
    closes = [float(i + 0.5) for i in range(30)]
    tenkan, kijun = compute_ichimoku(highs, lows, closes)
    assert tenkan[-1] is not None
    assert kijun[-1] is not None
