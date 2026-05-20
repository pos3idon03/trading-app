"""Walk-forward feature vectors for ML threshold/regime/surrogate models."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from features.quantitative_engine.mc_mtf import MtfBarContext

FEATURE_NAMES = [
    "adx_exec",
    "w_trend_exec",
    "regime_w_trend",
    "regime_adx",
    "structure_w_trend",
    "prob_raw",
    "prob_trend",
    "prob_reversion",
    "prob_rolling_p50",
    "prob_rolling_std",
    "rsi_exec",
    "atr_pct_exec",
    "ema_dist_exec",
]


@dataclass
class McFeatureRow:
    features: dict[str, float] = field(default_factory=dict)
    bar_index: int = 0


def _rsi(close: pd.Series, period: int = 14) -> float:
    if len(close) < period + 1:
        return 50.0
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean().iloc[-1]
    loss = (-delta.clip(upper=0)).rolling(period).mean().iloc[-1]
    if loss == 0 or not np.isfinite(loss):
        return 100.0 if gain > 0 else 50.0
    rs = gain / loss
    return float(100 - (100 / (1 + rs)))


def _atr_pct(df: pd.DataFrame, period: int = 14) -> float:
    if len(df) < period + 1:
        return 0.0
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    price = float(c.iloc[-1])
    return float(atr / price) if price > 0 and np.isfinite(atr) else 0.0


def _ema_dist(close: pd.Series, span: int = 20) -> float:
    if len(close) < 2:
        return 0.0
    ema = close.ewm(span=span, adjust=False).mean().iloc[-1]
    price = float(close.iloc[-1])
    if ema <= 0 or not np.isfinite(ema):
        return 0.0
    return float((price - ema) / ema)


def build_feature_row(
    bar_index: int,
    cal_df: pd.DataFrame,
    prob_raw: float | None,
    prob_trend: float | None,
    prob_reversion: float | None,
    mtf: MtfBarContext | None,
    adx_exec: float,
    w_trend_exec: float,
    prior_probs: list[float],
) -> McFeatureRow:
    """Features using only data available at bar close (walk-forward safe)."""
    feats: dict[str, float] = {
        "adx_exec": adx_exec if np.isfinite(adx_exec) else 20.0,
        "w_trend_exec": w_trend_exec,
        "prob_raw": prob_raw if prob_raw is not None else 0.5,
        "prob_trend": prob_trend if prob_trend is not None else 0.5,
        "prob_reversion": prob_reversion if prob_reversion is not None else 0.5,
        "rsi_exec": _rsi(cal_df["close"].astype(float)),
        "atr_pct_exec": _atr_pct(cal_df),
        "ema_dist_exec": _ema_dist(cal_df["close"].astype(float)),
    }
    if mtf:
        feats["regime_w_trend"] = mtf.regime_w_trend if mtf.regime_w_trend is not None else 0.5
        feats["regime_adx"] = mtf.regime_adx if mtf.regime_adx is not None else 20.0
        feats["structure_w_trend"] = mtf.structure_w_trend if mtf.structure_w_trend is not None else 0.5
    else:
        feats["regime_w_trend"] = w_trend_exec
        feats["regime_adx"] = feats["adx_exec"]
        feats["structure_w_trend"] = 0.5

    if prior_probs:
        arr = np.array(prior_probs, dtype=float)
        feats["prob_rolling_p50"] = float(np.median(arr))
        feats["prob_rolling_std"] = float(np.std(arr))
    else:
        feats["prob_rolling_p50"] = feats["prob_raw"]
        feats["prob_rolling_std"] = 0.0

    return McFeatureRow(features=feats, bar_index=bar_index)


def feature_vector(row: McFeatureRow) -> np.ndarray:
    return np.array([row.features.get(k, 0.0) for k in FEATURE_NAMES], dtype=float)
