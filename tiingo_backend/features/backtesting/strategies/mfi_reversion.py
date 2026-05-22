from typing import Any

from features.backtesting.indicators import compute_mfi


def generate_signal(
    bars: list[dict],
    indicators: list[str | None],
    params: dict[str, Any],
    index: int,
) -> str:
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    closes = [float(b["close"]) for b in bars]
    volumes = [float(b.get("volume") or 0.0) for b in bars]
    mfi = compute_mfi(highs, lows, closes, volumes, int(params["period"]))
    value = mfi[index]
    if value is None:
        return "hold"
    if value <= float(params["oversold"]):
        return "buy"
    if value >= float(params["overbought"]):
        return "sell"
    return "hold"
