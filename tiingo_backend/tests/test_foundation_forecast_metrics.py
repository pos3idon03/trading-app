from features.foundation.adapters.base import ForecastResult
from features.foundation.forecast_metrics import compute_forecast_metrics


def test_compute_forecast_metrics():
    series = [100.0, 101.0, 102.0, 103.0, 104.0]
    forecasts: list[ForecastResult | None] = [None] * 5
    forecasts[2] = ForecastResult(point=[103.0])
    forecasts[3] = ForecastResult(point=[105.0])
    stats = compute_forecast_metrics(series, forecasts, start_index=2, horizon=1)
    assert stats["evaluated_points"] == 2
    assert stats["mae"] is not None
    assert stats["directional_accuracy"] is not None
