from features.foundation.adapters.base import ForecastResult


def compute_forecast_metrics(
    series: list[float],
    forecasts: list[ForecastResult | None],
    *,
    start_index: int,
    horizon: int,
) -> dict:
    errors: list[float] = []
    pct_errors: list[float] = []
    direction_hits = 0
    direction_total = 0

    for index in range(start_index, len(series) - 1):
        forecast = forecasts[index] if index < len(forecasts) else None
        if forecast is None or not forecast.point:
            continue
        actual_next = series[index + 1]
        predicted = forecast.point[0]
        error = abs(predicted - actual_next)
        errors.append(error)
        if actual_next != 0:
            pct_errors.append(error / abs(actual_next))
        current = series[index]
        if current != 0 and actual_next != current:
            actual_dir = actual_next > current
            pred_dir = predicted > current
            direction_total += 1
            if actual_dir == pred_dir:
                direction_hits += 1

    evaluated = len(errors)
    if evaluated == 0:
        return {"mae": None, "mape": None, "directional_accuracy": None, "evaluated_points": 0}

    mae = sum(errors) / evaluated
    mape = (sum(pct_errors) / len(pct_errors) * 100) if pct_errors else None
    dir_acc = (direction_hits / direction_total) if direction_total else None
    return {
        "mae": round(mae, 6),
        "mape": round(mape, 4) if mape is not None else None,
        "directional_accuracy": round(dir_acc, 4) if dir_acc is not None else None,
        "evaluated_points": evaluated,
    }
