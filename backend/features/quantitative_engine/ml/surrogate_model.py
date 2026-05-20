"""Surrogate model approximating MC prob_positive_return."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from features.quantitative_engine.mc_features import McFeatureRow, feature_vector
from features.quantitative_engine.ml.model_io import load_sklearn_bundle, resolve_model_path


class SurrogateModelInference:
    """Fast approximation of 1-step prob_positive_return."""

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

    def predict_prob(self, row: McFeatureRow) -> float:
        if self._model is None:
            raise RuntimeError("Surrogate model not loaded")
        x = feature_vector(row).reshape(1, -1)
        pred = float(self._model.predict(x)[0])
        return float(np.clip(pred, 0.0, 1.0))


def train_surrogate_model(X: np.ndarray, y_prob: np.ndarray) -> object:
    from sklearn.ensemble import GradientBoostingRegressor

    model = GradientBoostingRegressor(n_estimators=80, max_depth=4, random_state=42)
    model.fit(X, y_prob)
    return model
