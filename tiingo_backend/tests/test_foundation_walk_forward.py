from features.foundation.adapters.base import ForecastResult
from features.foundation.walk_forward import run_walk_forward_forecasts


class MockAdapter:
    adapter_id = "mock"

    def load(self) -> None:
        return None

    def forecast(self, context: list[float], horizon: int) -> ForecastResult:
        last = context[-1]
        return ForecastResult(point=[last * 1.02] * horizon)


def test_walk_forward_uses_only_past_context():
    series = [float(i) for i in range(20)]
    adapter = MockAdapter()
    signals, forecasts = run_walk_forward_forecasts(
        series,
        adapter,
        context_length=5,
        forecast_horizon=2,
        signal_mode="next_point",
        buy_return_threshold=0.01,
        sell_return_threshold=-0.01,
    )
    assert signals[:5] == ["hold"] * 5
    assert forecasts[4] is None
    assert forecasts[5] is not None
    assert len(signals) == len(series)


def test_walk_forward_no_lookahead_in_context():
    seen_max_index = {"value": -1}

    class TrackingAdapter(MockAdapter):
        def forecast(self, context: list[float], horizon: int) -> ForecastResult:
            seen_max_index["value"] = max(seen_max_index["value"], len(context) - 1)
            return super().forecast(context, horizon)

    series = [10.0 + i for i in range(15)]
    signals, _ = run_walk_forward_forecasts(
        series,
        TrackingAdapter(),
        context_length=4,
        forecast_horizon=1,
        signal_mode="next_point",
        buy_return_threshold=0.5,
        sell_return_threshold=-0.5,
    )
    assert seen_max_index["value"] <= 14
    assert signals[0] == "hold"
