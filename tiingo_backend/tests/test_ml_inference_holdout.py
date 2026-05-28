from datetime import date, datetime, timezone

import pytest

from features.ml.inference_holdout import (
    build_holdout_train_metrics,
    collect_labeled_bar_indices,
    resolve_holdout_bars,
    resolve_inference_bar_load_range,
    resolve_inference_eval_scope,
    resolve_inference_window,
    split_holdout_indices,
    split_labeled_samples_by_indices,
)


def _bars(count: int) -> list[dict]:
    return [
        {
            "time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100 + index,
        }
        for index in range(count)
    ]


def test_collect_and_split_holdout_indices():
    feature_rows = [[1.0], [2.0], [3.0], [4.0], [5.0], None]
    labels = [0, 1, 0, 1, 0, None]
    labeled = collect_labeled_bar_indices(feature_rows, labels)
    train_indices, holdout_indices = split_holdout_indices(labeled, 2)
    assert train_indices == [0, 1, 2]
    assert holdout_indices == [3, 4]


def test_split_holdout_raises_when_insufficient_labeled_bars():
    with pytest.raises(ValueError, match="Insufficient labeled bars"):
        split_holdout_indices([0, 1, 2], 3)


def test_resolve_holdout_bars_uses_test_bars():
    assert resolve_holdout_bars({"test_bars": 42}) == 42


def test_build_holdout_train_metrics():
    bars = _bars(5)
    metadata = build_holdout_train_metrics(
        bars=bars,
        train_indices=[0, 1, 2],
        holdout_indices=[3, 4],
        holdout_bars=2,
        decision_timeframe="1d",
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end=datetime(2024, 1, 5, tzinfo=timezone.utc),
    )
    assert metadata["holdout_start_bar_index"] == 3
    assert metadata["train_sample_count"] == 3
    assert metadata["holdout_sample_count"] == 2


def test_resolve_inference_bar_load_range_uses_training_window():
    start, end = resolve_inference_bar_load_range(
        train_metrics={
            "start": "2020-01-01T00:00:00Z",
            "end": "2024-01-01T00:00:00Z",
        },
        request_start=None,
        request_end=None,
    )
    assert start is not None
    assert end is not None
    assert start.year == 2020
    assert end.year == 2024


def test_resolve_inference_window_holdout():
    start_index, metadata = resolve_inference_window(
        train_metrics={
            "holdout_start": "2024-04-01",
            "holdout_end": "2024-06-30",
            "train_end": "2024-03-31",
            "holdout_start_bar_index": 63,
            "holdout_bars": 63,
        },
        hyperparams={"test_bars": 63},
        inference_eval_scope="holdout",
    )
    assert start_index == 63
    assert metadata["evaluation_scope"] == "holdout"
    assert metadata["holdout_start_date"] == "2024-04-01"


def test_resolve_inference_window_legacy_model_raises():
    with pytest.raises(ValueError, match="Retrain this model"):
        resolve_inference_window(
            train_metrics={"start": "2024-01-01", "end": "2024-12-31"},
            hyperparams={"test_bars": 63},
            inference_eval_scope="holdout",
        )


def test_resolve_inference_window_in_sample():
    start_index, metadata = resolve_inference_window(
        train_metrics=None,
        hyperparams={"test_bars": 63},
        inference_eval_scope="in_sample",
    )
    assert start_index == 0
    assert metadata["evaluation_scope"] == "in_sample"


def test_resolve_inference_eval_scope_rejects_unknown():
    with pytest.raises(ValueError, match="inference_eval_scope"):
        resolve_inference_eval_scope({"inference_eval_scope": "invalid"})


def test_split_labeled_samples_by_indices():
    feature_rows = [[1.0], [2.0], [3.0]]
    labels = [0, 1, 0]
    x_rows, y_rows = split_labeled_samples_by_indices(feature_rows, labels, [0, 2])
    assert x_rows == [[1.0], [3.0]]
    assert y_rows == [0, 0]
