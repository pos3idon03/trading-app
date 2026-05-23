from typing import Optional

from features.backtesting.indicators import compute_rsi, compute_sma

# Bar-index warmup: lookbacks (ret_20, sma50, etc.) count bars, not calendar time.
FEATURE_WARMUP_BARS = 50

FEATURE_NAMES = [
    "ret_1",
    "ret_5",
    "ret_20",
    "vol_20",
    "rsi_14",
    "sma20_dist",
    "sma50_dist",
    "hl_range",
]


def _pct_return(closes: list[float], index: int, lookback: int) -> Optional[float]:
    if index < lookback or closes[index - lookback] == 0:
        return None
    return (closes[index] / closes[index - lookback]) - 1.0


def _rolling_vol(closes: list[float], index: int, period: int) -> Optional[float]:
    if index < period:
        return None
    returns = []
    for i in range(index - period + 1, index + 1):
        if closes[i - 1] == 0:
            return None
        returns.append((closes[i] / closes[i - 1]) - 1.0)
    if not returns:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / len(returns)
    return variance**0.5


def _sma_distance(
    closes: list[float],
    sma_values: list[Optional[float]],
    index: int,
) -> Optional[float]:
    sma = sma_values[index]
    if sma is None or sma == 0:
        return None
    return (closes[index] / sma) - 1.0


def build_price_feature_matrix(bars: list[dict]) -> tuple[list[str], list[Optional[list[float]]]]:
    if not bars:
        return FEATURE_NAMES, []

    closes = [float(b["close"]) for b in bars]
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    rsi = compute_rsi(closes, 14)
    sma20 = compute_sma(closes, 20)
    sma50 = compute_sma(closes, 50)

    rows: list[Optional[list[float]]] = []
    for index in range(len(bars)):
        if index < FEATURE_WARMUP_BARS:
            rows.append(None)
            continue

        ret_1 = _pct_return(closes, index, 1)
        ret_5 = _pct_return(closes, index, 5)
        ret_20 = _pct_return(closes, index, 20)
        vol_20 = _rolling_vol(closes, index, 20)
        rsi_14 = rsi[index]
        sma20_dist = _sma_distance(closes, sma20, index)
        sma50_dist = _sma_distance(closes, sma50, index)

        if closes[index] == 0:
            rows.append(None)
            continue
        hl_range = (highs[index] - lows[index]) / closes[index]

        values = [ret_1, ret_5, ret_20, vol_20, rsi_14, sma20_dist, sma50_dist, hl_range]
        if any(value is None for value in values):
            rows.append(None)
            continue
        rows.append([float(value) for value in values])

    return FEATURE_NAMES, rows
