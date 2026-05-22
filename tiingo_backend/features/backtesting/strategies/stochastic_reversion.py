from typing import Any

from features.backtesting.indicators import compute_stochastic


def generate_signal(
    bars: list[dict],
    indicators: list[str | None],
    params: dict[str, Any],
    index: int,
) -> str:
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    closes = [float(b["close"]) for b in bars]
    k_period = int(params["k_period"])
    d_period = int(params["d_period"])
    k_values, _ = compute_stochastic(highs, lows, closes, k_period, d_period)
    value = k_values[index]
    if value is None:
        return "hold"
    if value <= float(params["oversold"]):
        return "buy"
    if value >= float(params["overbought"]):
        return "sell"
    return "hold"
