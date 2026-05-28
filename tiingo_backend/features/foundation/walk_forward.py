from collections.abc import Callable
from typing import Any

from features.foundation.adapters.base import ForecastResult, FoundationAdapter
from features.foundation.signals import forecast_to_signal


def run_walk_forward_forecasts(
    series: list[float],
    adapter: FoundationAdapter,
    *,
    context_length: int,
    forecast_horizon: int,
    signal_mode: str,
    buy_return_threshold: float,
    sell_return_threshold: float,
    signal_prices: list[float] | None = None,
    on_progress: Callable[[int], None] | None = None,
    progress_interval: int = 10,
) -> tuple[list[str], list[ForecastResult | None]]:
    if context_length < 1:
        raise ValueError("context_length must be at least 1")

    prices = signal_prices if signal_prices is not None else series
    if len(prices) != len(series):
        raise ValueError("signal_prices length must match series length")

    signals = ["hold"] * len(series)
    forecasts: list[ForecastResult | None] = [None] * len(series)
    adapter.load()
    total = max(len(series) - context_length, 1)
    done = 0

    for index in range(context_length, len(series)):
        context = series[: index + 1]
        if len(context) > context_length:
            context = context[-context_length:]
        try:
            result = adapter.forecast(context, forecast_horizon)
        except Exception:
            result = None
        forecasts[index] = result
        price = prices[index]
        signals[index] = forecast_to_signal(
            price,
            result,
            signal_mode=signal_mode,
            buy_return_threshold=buy_return_threshold,
            sell_return_threshold=sell_return_threshold,
        )
        done += 1
        if on_progress and done % progress_interval == 0:
            pct = min(99, int(done / total * 90) + 5)
            on_progress(pct)

    if on_progress:
        on_progress(95)
    return signals, forecasts


def walk_forward_metadata(params: dict[str, Any], bar_count: int) -> dict[str, Any]:
    context_length = int(params["context_length"])
    return {
        "context_length": context_length,
        "forecast_horizon": int(params["forecast_horizon"]),
        "signal_mode": str(params["signal_mode"]),
        "target_series": str(params["target_series"]),
        "bars_evaluated": max(bar_count - context_length, 0),
        "warmup_bars": context_length,
    }
