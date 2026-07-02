from features.ml.evaluation import extract_coefficient_importance
from features.ml.trainer import train_model


def test_extract_coefficient_importance_logistic():
    x_rows = [[0.01, 50.0], [0.02, 60.0], [-0.01, 40.0], [0.03, 70.0]]
    y_rows = [0, 1, 0, 1]
    trained = train_model("ml_logistic", x_rows, y_rows, {})
    rows = extract_coefficient_importance(trained.model, ["ret_1", "rsi_14"])
    assert len(rows) == 2
    assert rows[0]["name"] in {"ret_1", "rsi_14"}
    assert rows[0]["value"] >= 0
