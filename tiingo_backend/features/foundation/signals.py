from features.foundation.adapters.base import ForecastResult


def predicted_return(
    current_price: float,
    forecast: list[float],
    *,
    signal_mode: str,
) -> float:
    if current_price <= 0 or not forecast:
        return 0.0
    if signal_mode == "horizon_mean":
        target = sum(forecast) / len(forecast)
    else:
        target = forecast[0]
    return (target - current_price) / current_price


def forecast_to_signal(
    current_price: float,
    forecast: ForecastResult | None,
    *,
    signal_mode: str,
    buy_return_threshold: float,
    sell_return_threshold: float,
) -> str:
    if forecast is None or not forecast.point:
        return "hold"
    ret = predicted_return(
        current_price,
        forecast.point,
        signal_mode=signal_mode,
    )
    if ret >= buy_return_threshold:
        return "buy"
    if ret <= sell_return_threshold:
        return "sell"
    return "hold"


def count_signals(signals: list[str]) -> dict[str, int]:
    counts = {"buy": 0, "sell": 0, "hold": 0}
    for signal in signals:
        counts[signal] = counts.get(signal, 0) + 1
    return counts
