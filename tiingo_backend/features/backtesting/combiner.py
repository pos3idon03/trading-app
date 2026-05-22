COMBINE_MODES = frozenset({"unanimous", "majority", "weighted"})


def combine_signals(
    signals: list[str],
    weights: list[float],
    mode: str,
    threshold: float,
) -> str:
    if not signals:
        return "hold"
    if mode not in COMBINE_MODES:
        raise ValueError(f"Unknown combine mode: {mode}")

    if mode == "unanimous":
        return _combine_unanimous(signals)
    if mode == "majority":
        return _combine_majority(signals)
    return _combine_weighted(signals, weights, threshold)


def _combine_unanimous(signals: list[str]) -> str:
    if all(signal == "buy" for signal in signals):
        return "buy"
    if all(signal == "sell" for signal in signals):
        return "sell"
    return "hold"


def _combine_majority(signals: list[str]) -> str:
    total = len(signals)
    buy_count = sum(1 for signal in signals if signal == "buy")
    sell_count = sum(1 for signal in signals if signal == "sell")
    if buy_count > total / 2:
        return "buy"
    if sell_count > total / 2:
        return "sell"
    return "hold"


def _combine_weighted(signals: list[str], weights: list[float], threshold: float) -> str:
    if len(weights) != len(signals):
        raise ValueError("weights length must match signals length")

    total_weight = sum(weights)
    if total_weight <= 0:
        return "hold"

    buy_weight = sum(weight for signal, weight in zip(signals, weights) if signal == "buy")
    sell_weight = sum(weight for signal, weight in zip(signals, weights) if signal == "sell")
    net = buy_weight - sell_weight
    cutoff = threshold * total_weight

    if net >= cutoff:
        return "buy"
    if net <= -cutoff:
        return "sell"
    return "hold"
