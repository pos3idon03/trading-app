import numpy as np
import pytest
from sklearn.pipeline import Pipeline

from features.ml.explainability import _build_explainer, _format_shap_values, _to_scalar_float
from features.ml.trainer import train_model


def test_to_scalar_float_from_multidim():
    assert _to_scalar_float(np.array([0.5, 0.6])) == 0.5


def test_format_shap_values_3d_array():
    values = np.array([
        [[0.1, 0.2], [0.3, 0.4]],
        [[0.5, 0.6], [0.7, 0.8]],
    ])
    rows = _format_shap_values(values, ["feat_a", "feat_b"], [0, 1])
    assert len(rows) == 4
    assert all(isinstance(row["mean_abs_shap"], float) for row in rows)
    assert {row["class_label"] for row in rows} == {"0", "1"}


def test_format_shap_values_2d_means_per_class():
    values = np.array([
        [0.1, 0.2],
        [0.3, 0.4],
    ])
    rows = _format_shap_values(values, ["feat_a", "feat_b"], [0, 1])
    assert len(rows) == 2
    assert rows[0]["mean_abs_shap"] == round(float(np.abs([0.1, 0.3]).mean()), 6)


def test_build_explainer_accepts_scaled_logistic_pipeline():
    x_rows = [[0.01, 50.0], [0.02, 60.0], [-0.01, 40.0], [0.03, 70.0]]
    y_rows = [0, 1, 0, 1]
    trained = train_model("ml_logistic", x_rows, y_rows, {})
    assert isinstance(trained.model, Pipeline)

    try:
        import shap
    except ImportError:  # pragma: no cover
        pytest.skip("shap not installed")

    x_array = np.array(x_rows)
    explainer = _build_explainer(trained.model, shap, x_array)
    assert explainer is not None
