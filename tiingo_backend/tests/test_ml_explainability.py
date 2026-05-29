import numpy as np
import pytest
from sklearn.pipeline import Pipeline

from features.ml.explainability import (
    _build_explainer,
    _extract_signed_shap_row,
    _format_shap_values,
    _to_scalar_float,
    compute_instance_contributions,
    compute_shap_importance,
)
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
    assert all(row["class_label"] == "1" for row in rows)
    assert rows[0]["mean_abs_shap"] == round(float(np.abs([0.1, 0.3]).mean()), 6)


def test_format_shap_values_binary_2d_assigns_positive_class():
    values = np.array([
        [0.1, 0.2],
        [0.3, 0.4],
    ])
    rows = _format_shap_values(values, ["feat_a", "feat_b"], [0, 1])
    assert {row["class_label"] for row in rows} == {"1"}


def test_format_shap_values_single_list_binary():
    values = [np.array([
        [0.1, 0.2],
        [0.3, 0.4],
    ])]
    rows = _format_shap_values(values, ["feat_a", "feat_b"], [0, 1])
    assert len(rows) == 2
    assert {row["class_label"] for row in rows} == {"1"}


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


def test_compute_instance_contributions_logistic():
    x_rows = [
        [0.01, 50.0],
        [0.02, 60.0],
        [-0.01, 40.0],
        [0.03, 70.0],
        [0.04, 65.0],
    ]
    y_rows = [0, 1, 0, 1, 1]
    trained = train_model("ml_logistic", x_rows, y_rows, {})
    classes = list(trained.model.named_steps["classifier"].classes_)

    try:
        import shap
    except ImportError:  # pragma: no cover
        pytest.skip("shap not installed")

    result = compute_instance_contributions(
        trained.model,
        x_rows[-1],
        x_rows,
        ["ret_1", "rsi_14"],
        classes,
        top_n=2,
    )
    assert result["method"] == "shap_linear"
    assert len(result["top_contributors"]) <= 2
    assert all("feature" in row and "contribution" in row for row in result["top_contributors"])


def test_compute_instance_contributions_tree_model():
    x_rows = [
        [0.01, 0.2],
        [0.02, 0.3],
        [-0.01, 0.1],
        [0.03, 0.4],
        [0.04, 0.35],
        [0.05, 0.25],
        [0.02, 0.15],
        [0.01, 0.18],
    ]
    y_rows = [0, 1, 0, 1, 1, 0, 1, 0]
    trained = train_model("ml_random_forest", x_rows, y_rows, {})
    classes = list(trained.model.classes_)

    try:
        import shap
    except ImportError:  # pragma: no cover
        pytest.skip("shap not installed")

    result = compute_instance_contributions(
        trained.model,
        x_rows[-1],
        x_rows,
        ["ret_1", "vol_20"],
        classes,
    )
    assert result["method"] == "shap_tree"
    assert result["top_contributors"]


def test_compute_instance_contributions_unavailable_for_knn():
    x_rows = [[0.1, 0.2], [0.2, 0.3], [0.3, 0.4], [0.4, 0.5]]
    y_rows = [0, 1, 0, 1]
    trained = train_model("ml_knn", x_rows, y_rows, {"knn_neighbors": 2})
    classes = list(trained.model.named_steps["classifier"].classes_)
    result = compute_instance_contributions(
        trained.model,
        x_rows[-1],
        x_rows,
        ["ret_1", "vol_20"],
        classes,
    )
    assert result["method"] == "unavailable"
    assert result["top_contributors"] == []


def test_extract_signed_shap_row_handles_1d_feature_vector():
    values = [np.array([0.1, -0.2, 0.3])]
    row = _extract_signed_shap_row(values, [0, 1], 1)
    assert row == [0.1, -0.2, 0.3]


def test_extract_signed_shap_row_clamps_3d_class_dimension():
    values = np.array([[[0.1, 0.2], [0.3, 0.4], [-0.1, -0.2]]])
    row = _extract_signed_shap_row(values, [0, 1], 1)
    assert row == [0.2, 0.4, -0.2]


def test_compute_instance_contributions_returns_unavailable_on_bad_shap_shape(monkeypatch):
    x_rows = [[0.01, 50.0], [0.02, 60.0], [-0.01, 40.0], [0.03, 70.0]]
    y_rows = [0, 1, 0, 1]
    trained = train_model("ml_logistic", x_rows, y_rows, {})
    classes = list(trained.model.named_steps["classifier"].classes_)

    class BrokenExplainer:
        def shap_values(self, _x):
            return []

    monkeypatch.setattr(
        "features.ml.explainability._build_explainer",
        lambda *_args, **_kwargs: BrokenExplainer(),
    )

    result = compute_instance_contributions(
        trained.model,
        x_rows[-1],
        x_rows,
        ["ret_1", "rsi_14"],
        classes,
    )
    assert result["method"] == "unavailable"
    assert any("parse failed" in warning for warning in result["warnings"])


def test_compute_shap_importance_scales_large_feature():
    x_rows = [
        [0.01, 1_000_000_000.0],
        [0.02, 2_000_000_000.0],
        [-0.01, 500_000_000.0],
        [0.03, 1_500_000_000.0],
        [0.01, 1_200_000_000.0],
    ]
    y_rows = [0, 1, 0, 1, 0]
    trained = train_model("ml_logistic", x_rows, y_rows, {})
    classes = list(trained.model.named_steps["classifier"].classes_)

    try:
        import shap
    except ImportError:  # pragma: no cover
        pytest.skip("shap not installed")

    rows = compute_shap_importance(
        trained.model,
        x_rows,
        ["ret_1", "revenue_level"],
        classes,
    )
    assert rows
    revenue_rows = [row for row in rows if row["feature"] == "revenue_level"]
    assert revenue_rows
    assert revenue_rows[0]["mean_abs_shap"] < 1_000_000.0
