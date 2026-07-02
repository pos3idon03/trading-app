from typing import Optional

from features.backtesting.indicators import (
    compute_atr,
    compute_bollinger_bands,
    compute_ema,
    compute_ichimoku,
    compute_macd,
    compute_obv,
    compute_rsi,
    compute_sma,
)
from features.ml.denoising import denoise_series

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
    "macd_line",
    "macd_signal",
    "macd_hist",
    "bb_pct_b",
    "bb_width",
    "obv_slope_5",
    "ichimoku_tenkan_dist",
    "ichimoku_kijun_dist",
    "volume_rel_20",
    "ema20_ema50_spread",
    "sma50_ema200_spread",
    "rsi_momentum",
]

VOLUME_REL_PERIOD = 20


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


def _ma_spread(
    fast_values: list[Optional[float]],
    slow_values: list[Optional[float]],
    index: int,
) -> Optional[float]:
    fast = fast_values[index]
    slow = slow_values[index]
    if fast is None or slow is None or slow == 0:
        return None
    return (fast - slow) / slow


def _rsi_momentum(
    rsi_values: list[Optional[float]],
    index: int,
    lookback: int = 5,
) -> Optional[float]:
    if index < lookback:
        return None
    current = rsi_values[index]
    prior = rsi_values[index - lookback]
    if current is None or prior is None:
        return None
    return current - prior


def _obv_slope(obv: list[float], index: int, lookback: int = 5) -> Optional[float]:
    if index < lookback or obv[index - lookback] == 0:
        return None
    return (obv[index] - obv[index - lookback]) / abs(obv[index - lookback])


def _volume_rel_20(
    volumes: list[float],
    index: int,
    period: int = VOLUME_REL_PERIOD,
) -> Optional[float]:
    if index < period - 1:
        return None
    window = volumes[index - period + 1 : index + 1]
    avg = sum(window) / len(window)
    if avg == 0:
        return None
    return volumes[index] / avg


def build_price_feature_matrix(
    bars: list[dict],
    *,
    denoise_method: str = "none",
    warmup_bars: int = FEATURE_WARMUP_BARS,
) -> tuple[list[str], list[Optional[list[float]]]]:
    if warmup_bars < 1:
        raise ValueError("warmup_bars must be at least 1")
    if not bars:
        return FEATURE_NAMES, []

    closes = denoise_series(
        [float(b["close"]) for b in bars],
        method=denoise_method if denoise_method in ("kalman", "wavelet") else "none",
    )
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    volumes = [float(b.get("volume") or 0.0) for b in bars]
    has_volume = any(v > 0 for v in volumes)

    rsi = compute_rsi(closes, 14)
    sma20 = compute_sma(closes, 20)
    sma50 = compute_sma(closes, 50)
    ema20 = compute_ema(closes, 20)
    ema50 = compute_ema(closes, 50)
    ema200 = compute_ema(closes, 200)
    atr = compute_atr(highs, lows, closes, 14)
    macd_line, macd_signal, macd_hist = compute_macd(closes)
    bb_mid, bb_upper, bb_lower = compute_bollinger_bands(closes, 20, 2.0)
    tenkan, kijun = compute_ichimoku(highs, lows, closes)
    obv = compute_obv(closes, volumes) if has_volume else [0.0] * len(closes)

    rows: list[Optional[list[float]]] = []
    for index in range(len(bars)):
        if index < warmup_bars:
            rows.append(None)
            continue

        close = closes[index]
        if close == 0:
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
        hl_range = (highs[index] - lows[index]) / close
        atr_norm = (atr_14 / close) if atr_14 is not None else None

        m_line = macd_line[index]
        m_signal = macd_signal[index]
        m_hist = macd_hist[index]
        macd_line_norm = (m_line / close) if m_line is not None else None
        macd_signal_norm = (m_signal / close) if m_signal is not None else None
        macd_hist_norm = (m_hist / close) if m_hist is not None else None

        upper = bb_upper[index]
        lower = bb_lower[index]
        mid = bb_mid[index]
        bb_pct_b = None
        bb_width = None
        if upper is not None and lower is not None and mid is not None and (upper - lower) > 0:
            bb_pct_b = (close - lower) / (upper - lower)
            bb_width = (upper - lower) / mid

        obv_slope_5 = _obv_slope(obv, index) if has_volume else 0.0
        tenkan_dist = _ma_distance(closes, tenkan, index)
        kijun_dist = _ma_distance(closes, kijun, index)
        volume_rel_20 = _volume_rel_20(volumes, index) if has_volume else 0.0
        ema20_ema50_spread = _ma_spread(ema20, ema50, index)
        sma50_ema200_spread = _ma_spread(sma50, ema200, index)
        rsi_momentum = _rsi_momentum(rsi, index)

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
            macd_line_norm,
            macd_signal_norm,
            macd_hist_norm,
            bb_pct_b,
            bb_width,
            obv_slope_5,
            tenkan_dist,
            kijun_dist,
            volume_rel_20,
            ema20_ema50_spread,
            sma50_ema200_spread,
            rsi_momentum,
        ]
        if any(value is None for value in values):
            rows.append(None)
            continue
        rows.append([float(value) for value in values])

    return FEATURE_NAMES, rows
