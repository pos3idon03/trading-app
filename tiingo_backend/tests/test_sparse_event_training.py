import pytest

from features.ml.models.lstm_classifier import LstmClassifier
from features.ml.sparse_event_training import (
    effective_lstm_seq_length,
    min_train_samples_for_fold,
)


def test_effective_lstm_seq_length_shrinks_for_short_series():
    assert effective_lstm_seq_length(32, 10) == 10
    assert effective_lstm_seq_length(32, 100) == 32
    assert effective_lstm_seq_length(32, 1) == 2


def test_min_train_samples_lower_for_sparse_meta_lstm():
    params = {"lstm_seq_length": 32, "meta_label_min_train_events": 6}
    sparse_min = min_train_samples_for_fold(
        "ml_lstm",
        params,
        sparse_events=True,
    )
    dense_min = min_train_samples_for_fold(
        "ml_lstm",
        params,
        sparse_events=False,
    )
    assert sparse_min == 8
    assert dense_min == 32


def test_lstm_fits_when_rows_below_default_seq_length():
    pytest.importorskip("torch")
    model = LstmClassifier(seq_length=32, epochs=1, num_layers=1)
    rows = [[float(i), float(i + 1)] for i in range(10)]
    labels = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    model.fit(rows, labels)
    proba = model.predict_proba(rows)
    assert proba.shape == (10, 2)
    assert model._fit_seq_length == 10
