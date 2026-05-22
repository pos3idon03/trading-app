from features.backtesting.strategies import (
    bollinger_breakout,
    donchian_breakout,
    mfi_reversion,
    stochastic_reversion,
    ts_momentum,
)


def _bar(
    close: float,
    high: float | None = None,
    low: float | None = None,
    volume: float = 1000.0,
) -> dict:
    return {
        "close": close,
        "high": high if high is not None else close + 1,
        "low": low if low is not None else close - 1,
        "volume": volume,
    }


def test_donchian_breakout_signals():
    bars = [_bar(10, 11, 9) for _ in range(4)]
    bars.append(_bar(20, 21, 19))
    signal = donchian_breakout.generate_signal(bars, [], {"channel_period": 3}, 4)
    assert signal == "buy"


def test_bollinger_breakout_signals():
    bars = [_bar(float(i), float(i) + 0.5, float(i) - 0.5) for i in range(1, 25)]
    bars[-1] = _bar(100.0, 101.0, 99.0)
    signal = bollinger_breakout.generate_signal(
        bars,
        [],
        {"period": 20, "std_dev": 2.0},
        len(bars) - 1,
    )
    assert signal == "buy"


def test_stochastic_reversion_signals():
    bars = [_bar(10, 11, 9) for _ in range(20)]
    bars[-1] = _bar(9, 9.5, 8.5)
    signal = stochastic_reversion.generate_signal(
        bars,
        [],
        {"k_period": 14, "d_period": 3, "oversold": 20, "overbought": 80},
        len(bars) - 1,
    )
    assert signal in {"buy", "sell", "hold"}


def test_mfi_reversion_signals():
    rising = [_bar(float(i), float(i) + 1, float(i) - 1, 1000.0) for i in range(1, 20)]
    signal = mfi_reversion.generate_signal(
        rising,
        [],
        {"period": 14, "oversold": 20, "overbought": 80},
        len(rising) - 1,
    )
    assert signal in {"buy", "sell", "hold"}


def test_ts_momentum_signals():
    up = [_bar(float(i)) for i in range(1, 70)]
    assert ts_momentum.generate_signal(up, [], {"lookback": 63}, 63) == "buy"
    down = [_bar(float(70 - i)) for i in range(70)]
    assert ts_momentum.generate_signal(down, [], {"lookback": 63}, 63) == "sell"
