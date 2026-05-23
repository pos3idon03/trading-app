from typing import Optional


def _forward_return(bars: list[dict], index: int, horizon: int, method: str) -> Optional[float]:
    closes = [float(b["close"]) for b in bars]
    future_index = index + horizon
    if future_index >= len(closes):
        return None
    if closes[index] == 0:
        return None
    if method == "mean":
        future_slice = closes[index + 1 : future_index + 1]
        if not future_slice:
            return None
        future_mean = sum(future_slice) / len(future_slice)
        return (future_mean / closes[index]) - 1.0
    return (closes[future_index] / closes[index]) - 1.0


def forward_return_at(
    bars: list[dict],
    index: int,
    horizon: int,
    *,
    label_method: str = "endpoint",
) -> Optional[float]:
    return _forward_return(bars, index, horizon, label_method)


def build_binary_labels(
    bars: list[dict],
    label_horizon: int,
    *,
    label_method: str = "endpoint",
) -> list[Optional[int]]:
    labels: list[Optional[int]] = []
    for index in range(len(bars)):
        forward_return = _forward_return(bars, index, label_horizon, label_method)
        if forward_return is None:
            labels.append(None)
            continue
        labels.append(1 if forward_return > 0 else 0)
    return labels


def build_ternary_labels(
    bars: list[dict],
    label_horizon: int,
    threshold: float,
    *,
    label_method: str = "endpoint",
) -> list[Optional[int]]:
    if threshold <= 0:
        raise ValueError("label_threshold must be positive for ternary labels")

    labels: list[Optional[int]] = []
    for index in range(len(bars)):
        forward_return = _forward_return(bars, index, label_horizon, label_method)
        if forward_return is None:
            labels.append(None)
            continue
        if forward_return >= threshold:
            labels.append(2)
        elif forward_return <= -threshold:
            labels.append(1)
        else:
            labels.append(0)
    return labels


def build_labels(
    bars: list[dict],
    label_horizon: int,
    *,
    label_mode: str = "binary",
    label_threshold: float = 0.01,
    label_method: str = "endpoint",
) -> list[Optional[int]]:
    if label_horizon < 1:
        raise ValueError("label_horizon must be at least 1")
    if label_mode == "ternary":
        return build_ternary_labels(
            bars,
            label_horizon,
            label_threshold,
            label_method=label_method,
        )
    return build_binary_labels(bars, label_horizon, label_method=label_method)


def build_forward_return_labels(
    bars: list[dict],
    label_horizon: int,
) -> list[Optional[int]]:
    return build_binary_labels(bars, label_horizon)


def label_distribution(labels: list[Optional[int]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in labels:
        if label is None:
            continue
        key = str(label)
        counts[key] = counts.get(key, 0) + 1
    return counts
