from typing import Any

from features.backtesting.indicators import compute_rsi


def generate_signal(
    bars: list[dict],
    indicators: list[str | None],
    params: dict[str, Any],
    index: int,
) -> str:
    closes = [float(b["close"]) for b in bars]
    rsi = compute_rsi(closes, int(params["period"]))
    value = rsi[index]
    if value is None:
        return "hold"
    if value <= float(params["oversold"]):
        return "buy"
    if value >= float(params["overbought"]):
        return "sell"
    return "hold"
