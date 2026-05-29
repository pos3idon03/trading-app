from typing import Any

from features.backtesting.strategies.registry import STRATEGY_CATALOG, get_signal_fn

DEFAULT_BASE_STRATEGY_ID = "crypto_trend_entry"
DEFAULT_BASE_STRATEGY_PARAMS = {
    "slow_period": 50,
    "rsi_period": 14,
    "rsi_max": 65.0,
}


def resolve_base_strategy_config(params: dict) -> tuple[str, dict[str, Any]]:
    strategy_id = str(params.get("base_strategy_id") or DEFAULT_BASE_STRATEGY_ID)
    if strategy_id not in STRATEGY_CATALOG:
        raise ValueError(f"Unknown base strategy id: {strategy_id}")

    raw_params = params.get("base_strategy_params") or {}
    merged = {**DEFAULT_BASE_STRATEGY_PARAMS, **raw_params}
    if strategy_id != "crypto_trend_entry":
        catalog_params = STRATEGY_CATALOG[strategy_id].get("params") or {}
        merged = {**catalog_params, **merged}
    return strategy_id, merged


def _raw_event_at_index(
    bars: list[dict],
    strategy_id: str,
    strategy_params: dict[str, Any],
    index: int,
) -> bool:
    signal_fn = get_signal_fn(strategy_id)
    signal = signal_fn(bars, [], strategy_params, index)
    return signal == "buy"


def build_event_mask(
    bars: list[dict],
    params: dict,
) -> list[bool]:
    if not bars:
        return []

    strategy_id, strategy_params = resolve_base_strategy_config(params)
    mask = [False] * len(bars)
    prev_active = False
    for index in range(len(bars)):
        active = _raw_event_at_index(bars, strategy_id, strategy_params, index)
        mask[index] = active and not prev_active
        prev_active = active
    return mask
