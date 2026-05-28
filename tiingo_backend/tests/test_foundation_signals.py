from features.foundation.adapters.base import ForecastResult
from features.foundation.signals import (
    count_signals,
    forecast_to_signal,
    predicted_return,
)


def test_predicted_return_next_point():
    ret = predicted_return(100.0, [102.0], signal_mode="next_point")
    assert abs(ret - 0.02) < 1e-9


def test_predicted_return_horizon_mean():
    ret = predicted_return(100.0, [101.0, 103.0], signal_mode="horizon_mean")
    assert abs(ret - 0.02) < 1e-9


def test_forecast_to_signal_buy_sell_hold():
    forecast = ForecastResult(point=[105.0])
    assert (
        forecast_to_signal(
            100.0,
            forecast,
            signal_mode="next_point",
            buy_return_threshold=0.01,
            sell_return_threshold=-0.01,
        )
        == "buy"
    )
    assert (
        forecast_to_signal(
            100.0,
            ForecastResult(point=[94.0]),
            signal_mode="next_point",
            buy_return_threshold=0.01,
            sell_return_threshold=-0.01,
        )
        == "sell"
    )
    assert (
        forecast_to_signal(
            100.0,
            ForecastResult(point=[100.5]),
            signal_mode="next_point",
            buy_return_threshold=0.01,
            sell_return_threshold=-0.01,
        )
        == "hold"
    )


def test_count_signals():
    counts = count_signals(["buy", "hold", "sell", "buy"])
    assert counts == {"buy": 2, "sell": 1, "hold": 1}
