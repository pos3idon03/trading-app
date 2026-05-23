import io

import pandas as pd
import pytest

from features.ml.training_export import (
    build_training_rows,
    training_rows_to_excel_bytes,
)


def _bars(closes: list[float]) -> list[dict]:
    return [{"time": f"2024-01-{index + 1:02d}", "close": price} for index, price in enumerate(closes)]


def test_build_training_rows_all_labeled():
    bars = _bars([100, 101, 102, 103, 104])
    features = [[1.0, 2.0], [1.1, 2.1], [1.2, 2.2], [1.3, 2.3], [1.4, 2.4]]
    labels = [0, 1, 0, 1, None]

    rows, warnings = build_training_rows(
        bars=bars,
        feature_names=["ret_1", "ret_5"],
        feature_rows=features,
        labels=labels,
        label_horizon=1,
        label_method="endpoint",
        scope="all_labeled",
    )

    assert len(rows) == 4
    assert rows[0]["ret_1"] == 1.0
    assert rows[0]["label"] in (0, 1)
    assert warnings == []


def test_build_training_rows_sample_limits_rows():
    bars = _bars([100 + index for index in range(20)])
    features = [[float(index)] for index in range(20)]
    labels = [0 if index % 2 == 0 else 1 for index in range(20)]

    rows, warnings = build_training_rows(
        bars=bars,
        feature_names=["ret_1"],
        feature_rows=features,
        labels=labels,
        label_horizon=1,
        label_method="endpoint",
        scope="sample",
        sample_size=5,
    )

    assert len(rows) == 5
    assert any("sample" in warning.lower() for warning in warnings)


def test_build_training_rows_oos_only_uses_test_windows():
    bars = _bars([100 + index for index in range(30)])
    features = [[float(index)] for index in range(30)]
    labels = [0 if index % 2 == 0 else 1 for index in range(30)]

    rows, _warnings = build_training_rows(
        bars=bars,
        feature_names=["ret_1"],
        feature_rows=features,
        labels=labels,
        label_horizon=1,
        label_method="endpoint",
        scope="oos_only",
        train_bars=10,
        test_bars=5,
        step_bars=5,
    )

    assert len(rows) == 5


def test_training_rows_to_excel_bytes_roundtrip():
    import io

    rows = [
        {"date": "2024-01-01", "ret_1": 0.1, "label": 1, "forward_return": 0.02},
        {"date": "2024-01-02", "ret_1": -0.2, "label": 0, "forward_return": -0.01},
    ]
    payload = training_rows_to_excel_bytes(rows)
    assert payload.startswith(b"PK")

    frame = pd.read_excel(io.BytesIO(payload), engine="openpyxl")
    assert len(frame) == 2
    assert "label" in frame.columns


def test_build_training_rows_raises_when_empty_oos():
    bars = _bars([100, 101])
    features = [[1.0], [1.1]]
    labels = [0, 1]

    rows, warnings = build_training_rows(
        bars=bars,
        feature_names=["ret_1"],
        feature_rows=features,
        labels=labels,
        label_horizon=1,
        label_method="endpoint",
        scope="oos_only",
        train_bars=10,
        test_bars=5,
        step_bars=5,
    )

    assert rows == []
    assert warnings
