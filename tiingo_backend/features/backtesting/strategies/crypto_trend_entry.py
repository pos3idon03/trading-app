from typing import Any

from features.backtesting.indicators import compute_ema, compute_rsi


def generate_signal(
    bars: list[dict],
    indicators: list[str | None],
    params: dict[str, Any],
    index: int,
) -> str:
    closes = [float(b["close"]) for b in bars]
    slow_period = int(params.get("slow_period", 50))
    rsi_period = int(params.get("rsi_period", 14))
    rsi_max = float(params.get("rsi_max", 65.0))

    slow_ema = compute_ema(closes, slow_period)
    rsi = compute_rsi(closes, rsi_period)
    if slow_ema[index] is None or rsi[index] is None:
        return "hold"

    close = closes[index]
    if close > slow_ema[index] and rsi[index] < rsi_max:
        return "buy"
    if close < slow_ema[index]:
        return "sell"
    return "hold"
