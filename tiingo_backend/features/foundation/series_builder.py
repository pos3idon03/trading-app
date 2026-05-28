import math
from typing import Any

from features.foundation.adapters.base import ForecastResult


def bar_close(bar: dict, target_series: str) -> float:
    if target_series == "adj_close":
        value = bar.get("adj_close") or bar.get("close")
    else:
        value = bar.get("close")
    if value is None:
        raise ValueError("Bar missing close price")
    return float(value)


def build_univariate_series(bars: list[dict], target_series: str) -> list[float]:
    if target_series == "log_return":
        return _log_return_series(bars)
    return [bar_close(bar, target_series) for bar in bars]


def _log_return_series(bars: list[dict]) -> list[float]:
    closes = [bar_close(bar, "close") for bar in bars]
    series: list[float] = [0.0]
    for index in range(1, len(closes)):
        prev = closes[index - 1]
        curr = closes[index]
        if prev <= 0 or curr <= 0:
            series.append(0.0)
        else:
            series.append(math.log(curr / prev))
    return series


def format_bar_date(bar: dict, timeframe: str) -> str:
    bar_time = bar["time"]
    daily_plus = frozenset({"1d", "1w", "1mo"})
    if timeframe in daily_plus:
        if hasattr(bar_time, "date"):
            return bar_time.date().isoformat()
        return str(bar_time)[:10]
    if hasattr(bar_time, "isoformat"):
        return bar_time.isoformat()
    return str(bar_time)


def sparse_forecast_samples(
    bars: list[dict],
    series: list[float],
    forecasts: list[ForecastResult | None],
    *,
    timeframe: str,
    stride: int,
    start_index: int,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for index in range(start_index, len(bars), max(1, stride)):
        forecast = forecasts[index] if index < len(forecasts) else None
        if forecast is None or not forecast.point:
            continue
        point = forecast.point[0]
        lower = forecast.lower[0] if forecast.lower else None
        upper = forecast.upper[0] if forecast.upper else None
        samples.append(
            {
                "date": format_bar_date(bars[index], timeframe),
                "actual": series[index] if index < len(series) else None,
                "forecast": point,
                "lower": lower,
                "upper": upper,
            }
        )
    return samples
