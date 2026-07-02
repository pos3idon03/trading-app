from features.backtesting.engine import run_backtest_with_signals
from features.backtesting.trade_exits import TradeExitConfig


def _bars(count: int, *, open_price: float = 100.0, high=101.0, low=99.0) -> list[dict]:
    return [
        {
            "time": f"2024-01-{index + 1:02d}",
            "open": open_price,
            "high": high,
            "low": low,
            "close": open_price,
            "volume": 1_000_000,
        }
        for index in range(count)
    ]


def test_max_hold_closes_long_position():
    bars = _bars(12)
    signals = ["buy"] + ["hold"] * 10 + ["hold"]
    config = TradeExitConfig(
        policy="label_horizon",
        max_hold_bars=3,
        profit_atr_mult=2.0,
        stop_atr_mult=1.5,
        atr_period=14,
    )
    result = run_backtest_with_signals(
        bars,
        signals,
        10_000.0,
        0.0,
        exit_config=config,
    )
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "max_hold"


def test_signal_only_allows_long_hold():
    bars = _bars(12)
    signals = ["buy"] + ["hold"] * 9 + ["sell", "hold"]
    config = TradeExitConfig(
        policy="signal_only",
        max_hold_bars=3,
        profit_atr_mult=2.0,
        stop_atr_mult=1.5,
        atr_period=14,
    )
    result = run_backtest_with_signals(
        bars,
        signals,
        10_000.0,
        0.0,
        exit_config=config,
    )
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "signal"
