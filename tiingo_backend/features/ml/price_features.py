from typing import Optional

from features.backtesting.indicators import compute_atr, compute_ema, compute_rsi, compute_sma

# Bar-index warmup: ema200 needs 200 bars before valid rows.
FEATURE_WARMUP_BARS = 200

FEATURE_NAMES = [
    "ret_1",
    "ret_5",
    "ret_20",
    "vol_20",
    "rsi_14",
    "sma20_dist",
    "sma50_dist",
    "hl_range",
    "atr_14",
    "ema20_dist",
    "ema50_dist",
    "ema200_dist",
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


def _ma_distance(
    closes: list[float],
    ma_values: list[Optional[float]],
    index: int,
) -> Optional[float]:
    ma = ma_values[index]
    if ma is None or ma == 0:
        return None
    return (closes[index] / ma) - 1.0


_sma_distance = _ma_distance


def build_price_feature_matrix(bars: list[dict]) -> tuple[list[str], list[Optional[list[float]]]]:
    if not bars:
        return FEATURE_NAMES, []

    closes = [float(b["close"]) for b in bars]
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    rsi = compute_rsi(closes, 14)
    sma20 = compute_sma(closes, 20)
    sma50 = compute_sma(closes, 50)
    ema20 = compute_ema(closes, 20)
    ema50 = compute_ema(closes, 50)
    ema200 = compute_ema(closes, 200)
    atr = compute_atr(highs, lows, closes, 14)

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
        sma20_dist = _ma_distance(closes, sma20, index)
        sma50_dist = _ma_distance(closes, sma50, index)
        ema20_dist = _ma_distance(closes, ema20, index)
        ema50_dist = _ma_distance(closes, ema50, index)
        ema200_dist = _ma_distance(closes, ema200, index)
        atr_14 = atr[index]

        if closes[index] == 0:
            rows.append(None)
            continue
        hl_range = (highs[index] - lows[index]) / closes[index]
        atr_norm = (atr_14 / closes[index]) if atr_14 is not None else None

        values = [
            ret_1,
            ret_5,
            ret_20,
            vol_20,
            rsi_14,
            sma20_dist,
            sma50_dist,
            hl_range,
            atr_norm,
            ema20_dist,
            ema50_dist,
            ema200_dist,
        ]
        if any(value is None for value in values):
            rows.append(None)
            continue
        rows.append([float(value) for value in values])

    return FEATURE_NAMES, rows
