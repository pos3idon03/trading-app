import io
import random
from datetime import datetime
from typing import Any, Literal

import pandas as pd

from features.ml.labels import build_labels, forward_return_at, label_distribution
from features.ml.splitter import build_walk_forward_windows

TrainingExportScope = Literal["all_labeled", "sample", "oos_only"]
MAX_EXPORT_ROWS = 50_000
DEFAULT_SAMPLE_SIZE = 500


def _bar_date(bar: dict) -> str:
    value = bar.get("time") or bar.get("date")
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def build_training_rows(
    *,
    bars: list[dict],
    feature_names: list[str],
    feature_rows: list,
    labels: list,
    label_horizon: int,
    label_method: str,
    scope: TrainingExportScope,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    train_bars: int = 252,
    test_bars: int = 63,
    step_bars: int = 63,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    oos_indices: set[int] = set()
    if scope == "oos_only":
        try:
            windows = build_walk_forward_windows(
                len(feature_rows),
                train_bars,
                test_bars,
                step_bars,
            )
            for _train, test_indices in windows:
                oos_indices.update(test_indices)
        except ValueError:
            oos_indices = set()

    for index, (bar, features, label) in enumerate(zip(bars, feature_rows, labels)):
        if features is None or label is None:
            continue
        if scope == "oos_only" and index not in oos_indices:
            continue

        forward_return = forward_return_at(
            bars, index, label_horizon, label_method=label_method,
        )
        row: dict[str, Any] = {
            "date": _bar_date(bar),
            "label": label,
            "forward_return": forward_return,
        }
        for name, value in zip(feature_names, features):
            row[name] = value
        rows.append(row)

    warnings: list[str] = []
    if scope == "sample" and len(rows) > sample_size:
        rows = random.sample(rows, sample_size)
        warnings.append(f"Exported random sample of {sample_size} rows.")

    if scope == "all_labeled" and len(rows) > MAX_EXPORT_ROWS:
        rows = rows[:MAX_EXPORT_ROWS]
        warnings.append(f"Export capped at {MAX_EXPORT_ROWS} rows.")

    if scope == "oos_only" and not rows:
        warnings.append("No OOS rows found for walk-forward windows.")

    return rows, warnings


def training_rows_to_excel_bytes(rows: list[dict[str, Any]]) -> bytes:
    frame = pd.DataFrame(rows)
    if not frame.empty and "date" in frame.columns:
        ordered = ["date", *[col for col in frame.columns if col not in {"date", "label", "forward_return"}]]
        if "label" in frame.columns:
            ordered.append("label")
        if "forward_return" in frame.columns:
            ordered.append("forward_return")
        frame = frame[[col for col in ordered if col in frame.columns]]

    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False, sheet_name="training_data")
    buffer.seek(0)
    return buffer.read()
