"""Tests for MC ML threshold/regime utilities."""
import numpy as np
import pytest

from features.quantitative_engine.mc_features import FEATURE_NAMES, McFeatureRow, feature_vector
from features.quantitative_engine.ml.threshold_model import (
    clamp_threshold_pair,
    expanding_percentile_thresholds,
    train_threshold_model,
)


class TestThresholdHelpers:
    def test_clamp_enforces_gap(self):
        buy, sell = clamp_threshold_pair(0.52, 0.51)
        assert buy - sell >= 0.03

    def test_expanding_percentile_insufficient_history(self):
        buy, sell = expanding_percentile_thresholds([0.5], 0.65, 0.4)
        assert buy == 0.65 and sell == 0.4

    def test_expanding_percentile_uses_prior(self):
        probs = [0.4 + i * 0.02 for i in range(12)]
        buy, sell = expanding_percentile_thresholds(probs, 0.65, 0.4)
        assert sell < buy


class TestTrainThresholdModel:
    def test_fit_predict_shape(self):
        rng = np.random.default_rng(0)
        n = 40
        X = rng.random((n, len(FEATURE_NAMES)))
        y_buy = np.full(n, 0.6)
        y_sell = np.full(n, 0.4)
        model = train_threshold_model(X, y_buy, y_sell)
        pred = model.predict(X[:1])[0]
        assert len(pred) == 2


class TestFeatureVector:
    def test_vector_length(self):
        row = McFeatureRow(features={k: 0.5 for k in FEATURE_NAMES})
        assert feature_vector(row).shape == (len(FEATURE_NAMES),)
