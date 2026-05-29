from typing import Optional


def _signal_from_class(class_label: int) -> str:
    if class_label == 2:
        return "buy"
    if class_label == 1:
        return "sell"
    return "hold"


def probabilities_to_signals(
    probabilities: list[Optional[float]],
    buy_threshold: float,
    sell_threshold: float,
) -> list[str]:
    if buy_threshold <= sell_threshold:
        raise ValueError("buy_threshold must be greater than sell_threshold")

    signals: list[str] = []
    for prob in probabilities:
        if prob is None:
            signals.append("hold")
            continue
        if prob >= buy_threshold:
            signals.append("buy")
        elif prob <= sell_threshold:
            signals.append("sell")
        else:
            signals.append("hold")
    return signals


def class_predictions_to_signals(
    predictions: list[Optional[int]],
    *,
    min_class_probability: float | None = None,
    class_probabilities: list[Optional[list[float]]] | None = None,
) -> list[str]:
    signals: list[str] = []
    for index, prediction in enumerate(predictions):
        if prediction is None:
            signals.append("hold")
            continue
        if min_class_probability is not None and class_probabilities is not None:
            probs = class_probabilities[index]
            if probs is None or max(probs) < min_class_probability:
                signals.append("hold")
                continue
        signals.append(_signal_from_class(int(prediction)))
    return signals


def predictions_to_signals(
    *,
    label_mode: str,
    probabilities: list[Optional[float]],
    class_predictions: list[Optional[int]] | None = None,
    buy_threshold: float,
    sell_threshold: float,
    min_class_probability: float | None = None,
    class_probabilities: list[Optional[list[float]]] | None = None,
) -> list[str]:
    if label_mode == "ternary":
        if class_predictions is None:
            raise ValueError("class_predictions required for ternary label_mode")
        return class_predictions_to_signals(
            class_predictions,
            min_class_probability=min_class_probability,
            class_probabilities=class_probabilities,
        )
    return probabilities_to_signals(probabilities, buy_threshold, sell_threshold)


def meta_gate_signals(
    event_mask: list[bool],
    probabilities: list[Optional[float]],
    threshold: float,
) -> list[str]:
    if len(event_mask) != len(probabilities):
        raise ValueError("event_mask and probabilities must have the same length")

    signals: list[str] = []
    for is_event, prob in zip(event_mask, probabilities):
        if not is_event or prob is None:
            signals.append("hold")
            continue
        signals.append("buy" if prob >= threshold else "hold")
    return signals


def count_signals(signals: list[str]) -> dict[str, int]:
    counts = {"buy": 0, "sell": 0, "hold": 0}
    for signal in signals:
        counts[signal] = counts.get(signal, 0) + 1
    return counts
