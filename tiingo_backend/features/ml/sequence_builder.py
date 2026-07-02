"""Build sequence windows from flat feature rows."""

from __future__ import annotations

from typing import Optional


def build_sequences(
    feature_rows: list[Optional[list[float]]],
    seq_length: int,
) -> tuple[list[list[list[float]]], list[int]]:
    sequences: list[list[list[float]]] = []
    indices: list[int] = []
    for index in range(len(feature_rows)):
        if index < seq_length - 1:
            continue
        window: list[list[float]] = []
        valid = True
        for j in range(index - seq_length + 1, index + 1):
            row = feature_rows[j]
            if row is None:
                valid = False
                break
            window.append(row)
        if valid:
            sequences.append(window)
            indices.append(index)
    return sequences, indices


def sequences_to_flat_batch(
    sequences: list[list[list[float]]],
) -> list[list[float]]:
    flat: list[list[float]] = []
    for seq in sequences:
        combined: list[float] = []
        for row in seq:
            combined.extend(row)
        flat.append(combined)
    return flat
