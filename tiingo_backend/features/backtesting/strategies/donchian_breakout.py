from typing import Any

from features.backtesting.indicators import compute_donchian


def generate_signal(
    bars: list[dict],
    indicators: list[str | None],
    params: dict[str, Any],
    index: int,
) -> str:
    period = int(params["channel_period"])
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    close = float(bars[index]["close"])
    upper, lower = compute_donchian(highs, lows, period)
    if upper[index] is None or lower[index] is None:
        return "hold"
    if close > upper[index]:
        return "buy"
    if close < lower[index]:
        return "sell"
    return "hold"
