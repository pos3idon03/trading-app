"""ML regime classifier for trend weight (replaces or augments ADX mapping)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from features.quantitative_engine.mc_features import McFeatureRow, feature_vector
from features.quantitative_engine.ml.model_io import load_sklearn_bundle, resolve_model_path
from features.quantitative_engine.regime_weight import trend_weight_from_adx

RegimeMode = str  # "adx" | "ml"


class RegimeModelInference:
    """Classifier or regressor outputting w_trend in [0, 1]."""

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

    def predict_w_trend(self, row: McFeatureRow, adx_fallback: float) -> float:
        if self._model is None:
            return trend_weight_from_adx(adx_fallback)
        x = feature_vector(row).reshape(1, -1)
        if hasattr(self._model, "predict_proba"):
            proba = self._model.predict_proba(x)[0]
            classes = list(getattr(self._model, "classes_", [0, 1, 2]))
            if 2 in classes:
                idx = classes.index(2)
                return float(np.clip(proba[idx], 0.0, 1.0))
            if 1 in classes:
                idx = classes.index(1)
                return float(np.clip(proba[idx], 0.0, 1.0))
        pred = float(self._model.predict(x)[0])
        return float(np.clip(pred, 0.0, 1.0))


def train_regime_model(X: np.ndarray, y_w_trend: np.ndarray) -> object:
    """Train gradient-boosted regressor for continuous w_trend."""
    from sklearn.ensemble import GradientBoostingRegressor

    model = GradientBoostingRegressor(n_estimators=50, max_depth=3, random_state=42)
    model.fit(X, y_w_trend)
    return model
