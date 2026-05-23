def build_walk_forward_windows(
    bar_count: int,
    train_bars: int,
    test_bars: int,
    step_bars: int,
) -> list[tuple[list[int], list[int]]]:
    if train_bars < 1 or test_bars < 1 or step_bars < 1:
        raise ValueError("train_bars, test_bars, and step_bars must be at least 1")

    minimum = train_bars + test_bars
    if bar_count < minimum:
        raise ValueError(
            f"Insufficient bars ({bar_count}) for walk-forward. "
            f"Minimum required: {minimum}"
        )

    windows: list[tuple[list[int], list[int]]] = []
    train_start = 0

    while True:
        train_end = train_start + train_bars
        test_end = train_end + test_bars
        if test_end > bar_count:
            break

        train_indices = list(range(train_start, train_end))
        test_indices = list(range(train_end, test_end))
        windows.append((train_indices, test_indices))
        train_start += step_bars

    if not windows:
        raise ValueError(
            f"Insufficient bars ({bar_count}) to produce walk-forward windows "
            f"with train={train_bars}, test={test_bars}, step={step_bars}"
        )

    return windows
