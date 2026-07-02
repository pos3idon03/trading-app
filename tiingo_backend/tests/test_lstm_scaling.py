import pytest

from features.ml.trainer import train_model


@pytest.fixture
def torch_available():
    pytest.importorskip("torch")


def test_lstm_fit_applies_scaling(torch_available):
    x_rows = [[index * 0.01, 50.0 + index] for index in range(40)]
    y_rows = [index % 2 for index in range(40)]
    params = {
        "lstm_seq_length": 8,
        "lstm_epochs": 2,
        "lstm_early_stopping_patience": 1,
        "lstm_validation_fraction": 0.2,
    }
    trained = train_model("ml_lstm", x_rows, y_rows, params)
    assert trained.model._scaler is not None
    probs = trained.model.predict_proba(x_rows)
    assert len(probs) == len(x_rows)
