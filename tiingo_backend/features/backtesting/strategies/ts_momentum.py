from typing import Any


def generate_signal(
    bars: list[dict],
    indicators: list[str | None],
    params: dict[str, Any],
    index: int,
) -> str:
    lookback = int(params["lookback"])
    if index < lookback:
        return "hold"
    current = float(bars[index]["close"])
    prior = float(bars[index - lookback]["close"])
    if prior == 0:
        return "hold"
    total_return = (current / prior) - 1.0
    if total_return > 0:
        return "buy"
    if total_return <= 0:
        return "sell"
    return "hold"
