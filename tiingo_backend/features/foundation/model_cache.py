from features.foundation.adapters.base import FoundationAdapter
from features.foundation.adapters.chronos import ChronosAdapter
from features.foundation.adapters.timesfm import TimesFmAdapter
from features.foundation.catalog import FOUNDATION_MODEL_CATALOG

_ADAPTER_CACHE: dict[str, FoundationAdapter] = {}


def _build_adapter(model_type: str) -> FoundationAdapter:
    meta = FOUNDATION_MODEL_CATALOG[model_type]
    adapter_key = meta["adapter"]
    checkpoint = meta["checkpoint"]
    if adapter_key == "timesfm":
        return TimesFmAdapter(checkpoint)
    if adapter_key == "chronos":
        return ChronosAdapter(checkpoint)
    raise ValueError(f"Unknown adapter key: {adapter_key}")


def get_foundation_adapter(model_type: str) -> FoundationAdapter:
    if model_type not in _ADAPTER_CACHE:
        _ADAPTER_CACHE[model_type] = _build_adapter(model_type)
    return _ADAPTER_CACHE[model_type]


def clear_adapter_cache() -> None:
    _ADAPTER_CACHE.clear()
