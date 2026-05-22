from datetime import datetime, timezone


def _bar_time(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def build_signal_index_map(
    decision_bars: list[dict],
    signal_bars: list[dict],
) -> list[int]:
    if not decision_bars:
        return []

    result: list[int] = []
    signal_idx = 0
    last_valid = -1

    for decision_bar in decision_bars:
        decision_time = _bar_time(decision_bar["time"])
        while signal_idx < len(signal_bars):
            if _bar_time(signal_bars[signal_idx]["time"]) <= decision_time:
                last_valid = signal_idx
                signal_idx += 1
                continue
            break
        result.append(last_valid)

    return result
