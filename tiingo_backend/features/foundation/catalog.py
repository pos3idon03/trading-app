from typing import Any

DEFAULT_FOUNDATION_PARAMS: dict[str, Any] = {
    "target_series": "close",
    "context_length": 128,
    "forecast_horizon": 5,
    "signal_mode": "next_point",
    "buy_return_threshold": 0.01,
    "sell_return_threshold": -0.01,
    "forecast_sample_stride": 10,
}

SUPPORTED_TARGET_SERIES = frozenset({"close", "adj_close", "log_return"})
SUPPORTED_SIGNAL_MODES = frozenset({"next_point", "horizon_mean"})

FOUNDATION_MODEL_CATALOG: dict[str, dict[str, Any]] = {
    "foundation_timesfm_2_5": {
        "label": "TimesFM 2.5 (200M)",
        "description": (
            "Google Research zero-shot time-series foundation model. "
            "Decoder-only transformer pretrained on 100B time-points."
        ),
        "adapter": "timesfm",
        "checkpoint": "google/timesfm-2.5-200m-pytorch",
        "params": DEFAULT_FOUNDATION_PARAMS,
        "constraints": {
            "context_length": (32, 1024),
            "forecast_horizon": (1, 256),
            "buy_return_threshold": (0.0001, 0.5),
            "sell_return_threshold": (-0.5, -0.0001),
            "forecast_sample_stride": (1, 100),
        },
    },
    "foundation_chronos_2": {
        "label": "Chronos-2 (120M)",
        "description": (
            "Amazon Science zero-shot forecasting foundation model. "
            "Encoder-only architecture with quantile forecasts."
        ),
        "adapter": "chronos",
        "checkpoint": "amazon/chronos-2",
        "params": DEFAULT_FOUNDATION_PARAMS,
        "constraints": {
            "context_length": (32, 512),
            "forecast_horizon": (1, 64),
            "buy_return_threshold": (0.0001, 0.5),
            "sell_return_threshold": (-0.5, -0.0001),
            "forecast_sample_stride": (1, 100),
        },
    },
}


def list_foundation_models() -> list[dict[str, Any]]:
    return [
        {"id": model_id, **meta}
        for model_id, meta in FOUNDATION_MODEL_CATALOG.items()
    ]


def get_foundation_model_catalog() -> list[dict]:
    return list_foundation_models()


def _clamp_param(key: str, value: float, bounds: tuple[float, float]) -> float:
    low, high = bounds
    if value < low or value > high:
        raise ValueError(f"{key} must be between {low} and {high}")
    return value


def validate_foundation_params(model_type: str, params: dict | None) -> dict:
    if model_type not in FOUNDATION_MODEL_CATALOG:
        supported = ", ".join(sorted(FOUNDATION_MODEL_CATALOG))
        raise ValueError(f"Unknown foundation model_type: {model_type}. Supported: {supported}")

    catalog = FOUNDATION_MODEL_CATALOG[model_type]
    merged = {**catalog["params"], **(params or {})}
    constraints = catalog.get("constraints", {})

    for key, bounds in constraints.items():
        if key not in merged:
            continue
        merged[key] = _clamp_param(key, float(merged[key]), bounds)

    target = str(merged.get("target_series") or "close")
    if target not in SUPPORTED_TARGET_SERIES:
        supported = ", ".join(sorted(SUPPORTED_TARGET_SERIES))
        raise ValueError(f"target_series must be one of: {supported}")

    signal_mode = str(merged.get("signal_mode") or "next_point")
    if signal_mode not in SUPPORTED_SIGNAL_MODES:
        supported = ", ".join(sorted(SUPPORTED_SIGNAL_MODES))
        raise ValueError(f"signal_mode must be one of: {supported}")

    buy_th = float(merged["buy_return_threshold"])
    sell_th = float(merged["sell_return_threshold"])
    if buy_th <= sell_th:
        raise ValueError("buy_return_threshold must be greater than sell_return_threshold")

    merged["target_series"] = target
    merged["signal_mode"] = signal_mode
    merged["context_length"] = int(merged["context_length"])
    merged["forecast_horizon"] = int(merged["forecast_horizon"])
    merged["forecast_sample_stride"] = int(merged["forecast_sample_stride"])
    return merged


def minimum_bars_required(params: dict) -> int:
    return int(params["context_length"]) + int(params["forecast_horizon"]) + 1
