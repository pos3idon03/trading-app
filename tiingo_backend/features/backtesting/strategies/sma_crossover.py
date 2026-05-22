from typing import Any

from features.backtesting.indicators import compute_sma


def generate_signal(
    bars: list[dict],
    indicators: list[str | None],
    params: dict[str, Any],
    index: int,
) -> str:
    closes = [float(b["close"]) for b in bars]
    fast = compute_sma(closes, int(params["fast_period"]))
    slow = compute_sma(closes, int(params["slow_period"]))
    if fast[index] is None or slow[index] is None:
        return "hold"
    if fast[index] > slow[index]:
        return "buy"
    if fast[index] < slow[index]:
        return "sell"
    return "hold"
