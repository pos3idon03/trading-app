import numpy as np
import pytest

from features.ml.explainability_advanced import (
    compute_pdp_curves,
    compute_shap_by_trade_slice,
    enrich_ml_summary_advanced,
    export_tree_rules,
)
from features.ml.trainer import train_model


def test_compute_pdp_curves_returns_grid():
    x_rows = [
        [0.1, 0.2],
        [0.2, 0.3],
        [0.3, 0.4],
        [0.4, 0.5],
        [0.5, 0.6],
        [0.2, 0.25],
    ]
    y_rows = [0, 1, 0, 1, 1, 0]
    trained = train_model("ml_random_forest", x_rows, y_rows, {})
    curves = compute_pdp_curves(
        trained.model,
        x_rows,
        ["ret_1", "vol_20"],
        top_features=["ret_1"],
        grid_points=5,
    )
    assert len(curves) == 1
    assert curves[0]["feature"] == "ret_1"
    assert len(curves[0]["grid"]) == 5
    assert len(curves[0]["p_up"]) == 5


def test_export_tree_rules_random_forest():
    x_rows = [[0.1, 0.2], [0.2, 0.3], [0.3, 0.4], [0.4, 0.5], [0.5, 0.6], [0.2, 0.25]]
    y_rows = [0, 1, 0, 1, 1, 0]
    trained = train_model("ml_random_forest", x_rows, y_rows, {})
    rules = export_tree_rules("ml_random_forest", trained.model, x_rows, ["ret_1", "vol_20"])
    assert rules is not None
    assert rules["format"] == "text"
    assert "ret_1" in rules["content"] or "|---" in rules["content"]


def test_compute_shap_by_trade_slice_empty_without_trades():
    x_rows = [[0.1, 0.2], [0.2, 0.3]]
    trained = train_model("ml_random_forest", x_rows, [0, 1], {})
    result = compute_shap_by_trade_slice(
        trained.model,
        x_rows,
        [0, 1],
        ["ret_1", "vol_20"],
        [0, 1],
        [],
        [{"time": "2020-01-01"}, {"time": "2020-01-02"}],
        model_type="ml_random_forest",
    )
    assert result == {}


def test_enrich_ml_summary_advanced_adds_keys(monkeypatch):
    x_rows = [
        [0.1, 0.2],
        [0.2, 0.3],
        [0.3, 0.4],
        [0.4, 0.5],
        [0.5, 0.6],
        [0.2, 0.25],
        [0.15, 0.22],
        [0.25, 0.28],
    ]
    y_rows = [0, 1, 0, 1, 1, 0, 1, 0]
    trained = train_model("ml_random_forest", x_rows, y_rows, {})

    monkeypatch.setattr(
        "features.ml.explainability_advanced.compute_shap_interactions",
        lambda *_a, **_k: [{"feature_a": "ret_1", "feature_b": "vol_20", "strength": 0.1}],
    )
    monkeypatch.setattr(
        "features.ml.explainability_advanced.compute_pdp_curves",
        lambda *_a, **_k: [{"feature": "ret_1", "grid": [0.1], "p_up": [0.5]}],
    )
    monkeypatch.setattr(
        "features.ml.explainability_advanced.compute_shap_by_trade_slice",
        lambda *_a, **_k: {"winners_top_decile": [], "losers_bottom_decile": []},
    )
    monkeypatch.setattr(
        "features.ml.explainability_advanced.export_tree_rules",
        lambda *_a, **_k: {"format": "text", "content": "rule", "max_depth": 4},
    )

    summary = enrich_ml_summary_advanced(
        ml_summary={
            "model_type": "ml_random_forest",
            "feature_names": ["ret_1", "vol_20"],
            "confusion_labels": [0, 1],
            "shap_importance": [{"class_label": "1", "feature": "ret_1", "mean_abs_shap": 0.2}],
            "macro_warnings": [],
        },
        importance_model=trained.model,
        oos_x_rows=x_rows,
        oos_bar_indices=list(range(len(x_rows))),
        trades=[],
        bars=[{"time": f"2020-01-{index + 1:02d}"} for index in range(len(x_rows))],
    )
    assert summary["shap_interactions"]
    assert summary["partial_dependence"]
    assert summary["tree_rules"]
