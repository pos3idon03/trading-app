from typing import Optional


def compute_sma(values: list[float], period: int) -> list[Optional[float]]:
    if period < 1 or not values:
        return [None] * len(values)

    result: list[Optional[float]] = []
    for i in range(len(values)):
        if i + 1 < period:
            result.append(None)
            continue
        window = values[i + 1 - period : i + 1]
        result.append(sum(window) / period)
    return result


def compute_ema(values: list[float], period: int) -> list[Optional[float]]:
    if period < 1 or not values:
        return [None] * len(values)

    multiplier = 2 / (period + 1)
    result: list[Optional[float]] = []
    ema: Optional[float] = None

    for i in range(len(values)):
        if i + 1 < period:
            result.append(None)
            continue
        if ema is None:
            seed = values[i + 1 - period : i + 1]
            ema = sum(seed) / period
            result.append(ema)
            continue
        ema = (values[i] - ema) * multiplier + ema
        result.append(ema)
    return result


def compute_rsi(values: list[float], period: int) -> list[Optional[float]]:
    if period < 1 or len(values) < period + 1:
        return [None] * len(values)

    result: list[Optional[float]] = [None] * period
    gains: list[float] = []
    losses: list[float] = []

    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result.append(_rsi_from_averages(avg_gain, avg_loss))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        result.append(_rsi_from_averages(avg_gain, avg_loss))

    return result


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_donchian(
    highs: list[float],
    lows: list[float],
    period: int,
) -> tuple[list[Optional[float]], list[Optional[float]]]:
    if period < 1 or not highs:
        empty = [None] * len(highs)
        return empty, empty

    upper: list[Optional[float]] = []
    lower: list[Optional[float]] = []
    for i in range(len(highs)):
        if i < period:
            upper.append(None)
            lower.append(None)
            continue
        window_highs = highs[i - period : i]
        window_lows = lows[i - period : i]
        upper.append(max(window_highs))
        lower.append(min(window_lows))
    return upper, lower


def compute_bollinger_bands(
    values: list[float],
    period: int,
    std_dev: float,
) -> tuple[list[Optional[float]], list[Optional[float]], list[Optional[float]]]:
    middle = compute_sma(values, period)
    upper: list[Optional[float]] = []
    lower: list[Optional[float]] = []

    for i in range(len(values)):
        mid = middle[i]
        if mid is None:
            upper.append(None)
            lower.append(None)
            continue
        window = values[i + 1 - period : i + 1]
        variance = sum((value - mid) ** 2 for value in window) / period
        band = std_dev * variance**0.5
        upper.append(mid + band)
        lower.append(mid - band)
    return middle, upper, lower


def compute_stochastic(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    k_period: int,
    d_period: int,
) -> tuple[list[Optional[float]], list[Optional[float]]]:
    if k_period < 1 or d_period < 1 or not closes:
        empty = [None] * len(closes)
        return empty, empty

    raw_k: list[Optional[float]] = []
    for i in range(len(closes)):
        if i + 1 < k_period:
            raw_k.append(None)
            continue
        window_highs = highs[i + 1 - k_period : i + 1]
        window_lows = lows[i + 1 - k_period : i + 1]
        highest = max(window_highs)
        lowest = min(window_lows)
        if highest == lowest:
            raw_k.append(50.0)
        else:
            raw_k.append(100.0 * (closes[i] - lowest) / (highest - lowest))

    d_series: list[Optional[float]] = []
    for i in range(len(raw_k)):
        if raw_k[i] is None or i + 1 < d_period:
            d_series.append(None)
            continue
        window = raw_k[i + 1 - d_period : i + 1]
        if any(value is None for value in window):
            d_series.append(None)
            continue
        d_series.append(sum(value for value in window if value is not None) / d_period)
    return raw_k, d_series


def compute_mfi(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    period: int,
) -> list[Optional[float]]:
    if period < 1 or len(closes) < period + 1:
        return [None] * len(closes)

    typical_prices = [
        (highs[i] + lows[i] + closes[i]) / 3.0 for i in range(len(closes))
    ]
    money_flows = [typical_prices[i] * volumes[i] for i in range(len(closes))]

    result: list[Optional[float]] = [None] * period
    for i in range(period, len(closes)):
        positive = 0.0
        negative = 0.0
        for j in range(i - period + 1, i + 1):
            if typical_prices[j] > typical_prices[j - 1]:
                positive += money_flows[j]
            elif typical_prices[j] < typical_prices[j - 1]:
                negative += money_flows[j]
        if negative == 0:
            result.append(100.0 if positive > 0 else 50.0)
        else:
            ratio = positive / negative
            result.append(100.0 - (100.0 / (1.0 + ratio)))
    return result
