from typing import Any

from features.backtesting.indicators import compute_bollinger_bands


def generate_signal(
    bars: list[dict],
    indicators: list[str | None],
    params: dict[str, Any],
    index: int,
) -> str:
    closes = [float(b["close"]) for b in bars]
    period = int(params["period"])
    std_dev = float(params["std_dev"])
    _, upper, lower = compute_bollinger_bands(closes, period, std_dev)
    close = closes[index]
    if upper[index] is None or lower[index] is None:
        return "hold"
    if close > upper[index]:
        return "buy"
    if close < lower[index]:
        return "sell"
    return "hold"
