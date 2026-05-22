from typing import Any


def generate_signal(
    bars: list[dict],
    indicators: list[str | None],
    params: dict[str, Any],
    index: int,
) -> str:
    if index == 0:
        return "buy"
    return "hold"
