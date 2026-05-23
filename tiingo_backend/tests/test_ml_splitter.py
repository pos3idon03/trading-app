import pytest

from features.ml.splitter import build_walk_forward_windows


def test_build_walk_forward_windows_produces_expected_ranges():
    windows = build_walk_forward_windows(
        bar_count=400,
        train_bars=100,
        test_bars=50,
        step_bars=50,
    )
    assert len(windows) >= 1
    train_indices, test_indices = windows[0]
    assert train_indices == list(range(0, 100))
    assert test_indices == list(range(100, 150))


def test_insufficient_bars_raises():
    with pytest.raises(ValueError):
        build_walk_forward_windows(
            bar_count=50,
            train_bars=100,
            test_bars=50,
            step_bars=50,
        )
