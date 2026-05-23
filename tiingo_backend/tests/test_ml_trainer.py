import warnings

import numpy as np
import pytest
from sklearn.pipeline import Pipeline

from features.ml.trainer import (
    _create_model,
    _resolve_classifier,
    predict_class_probabilities,
    train_model,
)


def _mixed_scale_data(count: int = 120) -> tuple[list[list[float]], list[int]]:
    rng = np.random.default_rng(42)
    x_rows = [
        [rng.uniform(-0.05, 0.05), rng.uniform(0, 100), rng.uniform(-1000, 1000)]
        for _ in range(count)
    ]
    y_rows = [1 if row[0] > 0 else 0 for row in x_rows]
    return x_rows, y_rows


@pytest.mark.parametrize("model_type", ["ml_logistic", "ml_knn"])
def test_create_model_returns_scaled_pipeline(model_type: str):
    model = _create_model(model_type, {})
    assert isinstance(model, Pipeline)
    assert "scaler" in model.named_steps
    assert "classifier" in model.named_steps


def test_logistic_trains_without_convergence_warning():
    x_rows, y_rows = _mixed_scale_data()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = train_model("ml_logistic", x_rows, y_rows, {})
    convergence = [
        item for item in caught
        if item.category.__name__ == "ConvergenceWarning"
    ]
    assert not convergence
    assert result.train_accuracy > 0
    assert isinstance(result.model, Pipeline)


def test_knn_pipeline_predicts():
    x_rows, y_rows = _mixed_scale_data(count=40)
    result = train_model("ml_knn", x_rows, y_rows, {"knn_neighbors": 3})
    probs = predict_class_probabilities(result.model, x_rows[:5])
    assert len(probs) == 5
    assert all(len(row) >= 2 for row in probs)


def test_resolve_classifier_unwraps_pipeline():
    x_rows, y_rows = _mixed_scale_data(count=40)
    pipeline = _create_model("ml_logistic", {})
    pipeline.fit(x_rows, y_rows)
    classifier = _resolve_classifier(pipeline)
    assert hasattr(classifier, "coef_")
    assert classifier is pipeline.named_steps["classifier"]
