from features.ml.evaluation import build_roc_curves, compute_classification_metrics


def test_compute_classification_metrics_includes_f1_macro():
    metrics = compute_classification_metrics([0, 1, 2], [0, 1, 1])
    assert metrics["f1_macro"] is not None


def test_build_roc_curves_binary():
    curves, auc_scores = build_roc_curves([0, 1, 1, 0], [[0.2, 0.8], [0.3, 0.7], [0.4, 0.6], [0.6, 0.4]], [0, 1])
    assert curves
    assert "macro" in auc_scores
