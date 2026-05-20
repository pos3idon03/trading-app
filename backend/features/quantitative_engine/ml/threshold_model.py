"""Dynamic buy/sell threshold prediction from MTF features."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np

MIN_THRESHOLD_GAP = 0.03
from features.quantitative_engine.mc_features import FEATURE_NAMES, McFeatureRow, feature_vector
from features.quantitative_engine.ml.model_io import load_sklearn_bundle, resolve_model_path

ThresholdMode = Literal["static", "ml_dynamic", "suggested_percentile"]


def clamp_threshold_pair(buy: float, sell: float) -> tuple[float, float]:
    buy = round(min(max(float(buy), 0.01), 0.99), 4)
    sell = round(min(max(float(sell), 0.01), 0.99), 4)
    if buy - sell < MIN_THRESHOLD_GAP:
        mid = (buy + sell) / 2
        buy = round(min(0.99, mid + MIN_THRESHOLD_GAP / 2), 4)
        sell = round(max(0.01, mid - MIN_THRESHOLD_GAP / 2), 4)
    if sell >= buy:
        sell = max(0.01, round(buy - MIN_THRESHOLD_GAP, 4))
    return buy, sell


def expanding_percentile_thresholds(
    prior_probs: list[float],
    default_buy: float,
    default_sell: float,
) -> tuple[float, float]:
    """Walk-forward safe suggested thresholds from probs seen so far."""
    if len(prior_probs) < 10:
        return default_buy, default_sell
    arr = np.array(prior_probs, dtype=float)
    buy, sell = float(np.percentile(arr, 75)), float(np.percentile(arr, 25))
    return clamp_threshold_pair(buy, sell)


class ThresholdModelInference:
    """Ridge (or compatible) model predicting buy and sell thresholds."""

    def __init__(self, model_path: str | Path | None = None):
        self._model = None
        self._metadata: dict = {}
        if model_path:
            self.load(model_path)

    def load(self, path: str | Path) -> None:
        resolved = Path(path) if Path(path).is_absolute() else resolve_model_path(str(path))
        self._model, self._metadata = load_sklearn_bundle(resolved)

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def predict(self, row: McFeatureRow) -> tuple[float, float]:
        if self._model is None:
            raise RuntimeError("Threshold model not loaded")
        x = feature_vector(row).reshape(1, -1)
        pred = self._model.predict(x)[0]
        if len(pred) >= 2:
            return clamp_threshold_pair(float(pred[0]), float(pred[1]))
        mid = float(pred[0]) if len(pred) else 0.55
        return clamp_threshold_pair(mid + MIN_THRESHOLD_GAP / 2, mid - MIN_THRESHOLD_GAP / 2)


def train_threshold_model(
    X: np.ndarray,
    y_buy: np.ndarray,
    y_sell: np.ndarray,
) -> object:
    """Train multi-output ridge regressor for thresholds."""
    from sklearn.linear_model import Ridge
    from sklearn.multioutput import MultiOutputRegressor

    y = np.column_stack([y_buy, y_sell])
    model = MultiOutputRegressor(Ridge(alpha=1.0))
    model.fit(X, y)
    return model
