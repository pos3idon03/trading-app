from typing import Any, Callable

from features.backtesting.strategies import (
    bollinger_breakout,
    buy_and_hold,
    crypto_trend_entry,
    donchian_breakout,
    ema_crossover,
    ensemble,
    mfi_reversion,
    rsi_reversion,
    sma_crossover,
    stochastic_reversion,
    ts_momentum,
)
from features.backtesting.bar_loader import validate_timeframe

SignalFn = Callable[[list[dict], list[str | None], dict[str, Any], int], str]

ENSEMBLE_LEG_STRATEGIES = frozenset(
    {
        "sma_crossover",
        "ema_crossover",
        "rsi_reversion",
        "donchian_breakout",
        "bollinger_breakout",
        "stochastic_reversion",
        "mfi_reversion",
        "ts_momentum",
    }
)
COMBINE_MODES = frozenset({"unanimous", "majority", "weighted"})
MIN_ENSEMBLE_LEGS = 2
MAX_ENSEMBLE_LEGS = 5

DEFAULT_ENSEMBLE_LEGS = [
    {
        "strategy_id": "sma_crossover",
        "params": {"fast_period": 20, "slow_period": 50},
        "weight": 1.0,
    },
    {
        "strategy_id": "rsi_reversion",
        "params": {"period": 14, "oversold": 30, "overbought": 70},
        "weight": 1.0,
    },
]

STRATEGY_CATALOG: dict[str, dict[str, Any]] = {
    "buy_and_hold": {
        "label": "Buy and Hold",
        "description": "Enter on first bar and hold through the period.",
        "params": {},
        "constraints": {},
        "min_bars": 1,
        "ensemble_eligible": False,
        "signal_fn": buy_and_hold.generate_signal,
    },
    "sma_crossover": {
        "label": "SMA Crossover",
        "description": "Long when fast SMA crosses above slow SMA.",
        "params": {"fast_period": 20, "slow_period": 50},
        "constraints": {"fast_period": (5, 200), "slow_period": (10, 400)},
        "min_bars": 51,
        "ensemble_eligible": True,
        "signal_fn": sma_crossover.generate_signal,
    },
    "ema_crossover": {
        "label": "EMA Crossover",
        "description": "Long when fast EMA crosses above slow EMA.",
        "params": {"fast_period": 12, "slow_period": 26},
        "constraints": {"fast_period": (5, 200), "slow_period": (10, 400)},
        "min_bars": 27,
        "ensemble_eligible": True,
        "signal_fn": ema_crossover.generate_signal,
    },
    "rsi_reversion": {
        "label": "RSI Mean Reversion",
        "description": "Buy oversold, sell overbought.",
        "params": {"period": 14, "oversold": 30, "overbought": 70},
        "constraints": {
            "period": (2, 100),
            "oversold": (5, 45),
            "overbought": (55, 95),
        },
        "min_bars": 16,
        "ensemble_eligible": True,
        "signal_fn": rsi_reversion.generate_signal,
    },
    "donchian_breakout": {
        "label": "Donchian Breakout",
        "description": (
            "Trend-following breakout using prior N-bar high/low channels. "
            "Long-only; exits to cash on breakdown."
        ),
        "params": {"channel_period": 20},
        "constraints": {"channel_period": (5, 200)},
        "min_bars": 21,
        "ensemble_eligible": True,
        "signal_fn": donchian_breakout.generate_signal,
    },
    "bollinger_breakout": {
        "label": "Bollinger Breakout",
        "description": (
            "Trend-following breakout when price closes outside Bollinger bands. "
            "Long-only in this backtest engine."
        ),
        "params": {"period": 20, "std_dev": 2.0},
        "constraints": {"period": (5, 200), "std_dev": (0.5, 4.0)},
        "min_bars": 21,
        "ensemble_eligible": True,
        "signal_fn": bollinger_breakout.generate_signal,
    },
    "stochastic_reversion": {
        "label": "Stochastic Mean Reversion",
        "description": "Buy when %K is oversold, sell when %K is overbought.",
        "params": {
            "k_period": 14,
            "d_period": 3,
            "oversold": 20,
            "overbought": 80,
        },
        "constraints": {
            "k_period": (2, 100),
            "d_period": (2, 50),
            "oversold": (5, 45),
            "overbought": (55, 95),
        },
        "min_bars": 17,
        "ensemble_eligible": True,
        "signal_fn": stochastic_reversion.generate_signal,
    },
    "mfi_reversion": {
        "label": "MFI Mean Reversion",
        "description": "Money Flow Index mean reversion using price and volume.",
        "params": {"period": 14, "oversold": 20, "overbought": 80},
        "constraints": {
            "period": (2, 100),
            "oversold": (5, 45),
            "overbought": (55, 95),
        },
        "min_bars": 16,
        "ensemble_eligible": True,
        "signal_fn": mfi_reversion.generate_signal,
    },
    "crypto_trend_entry": {
        "label": "Crypto Trend Entry",
        "description": (
            "Long when close is above slow EMA and RSI is below overbought threshold. "
            "Used as the base rule for meta-label training."
        ),
        "params": {"slow_period": 50, "rsi_period": 14, "rsi_max": 65.0},
        "constraints": {
            "slow_period": (10, 200),
            "rsi_period": (2, 100),
            "rsi_max": (50.0, 90.0),
        },
        "min_bars": 51,
        "ensemble_eligible": False,
        "signal_fn": crypto_trend_entry.generate_signal,
    },
    "ts_momentum": {
        "label": "Time-Series Momentum",
        "description": (
            "CTA-style trend: long when N-bar return is positive, exit when non-positive. "
            "Long-only; does not short negative-momentum assets."
        ),
        "params": {"lookback": 63},
        "constraints": {"lookback": (5, 400)},
        "min_bars": 64,
        "ensemble_eligible": True,
        "signal_fn": ts_momentum.generate_signal,
    },
    "strategy_ensemble": {
        "label": "Strategy Ensemble",
        "description": (
            "Combine 2–5 signal strategies. Unanimous requires all legs to agree; "
            "majority uses a strict vote; weighted uses net buy/sell score with a threshold."
        ),
        "params": {
            "combine_mode": "majority",
            "threshold": 0.5,
            "legs": DEFAULT_ENSEMBLE_LEGS,
        },
        "constraints": {"threshold": (0.1, 1.0)},
        "min_bars": 51,
        "ensemble_eligible": False,
        "signal_fn": ensemble.generate_signal,
    },
}


def list_strategies() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key, meta in STRATEGY_CATALOG.items():
        items.append(
            {
                "id": key,
                "label": meta["label"],
                "description": meta["description"],
                "params": meta["params"],
                "constraints": meta.get("constraints", {}),
                "ensemble_eligible": meta.get("ensemble_eligible", False),
            }
        )
    return items


def resolve_strategy(strategy_id: str) -> dict[str, Any]:
    if strategy_id not in STRATEGY_CATALOG:
        raise ValueError(f"Unknown strategy: {strategy_id}")
    return STRATEGY_CATALOG[strategy_id]


def _validate_scalar_params(strategy_id: str, params: dict[str, Any] | None) -> dict[str, Any]:
    meta = resolve_strategy(strategy_id)
    defaults = dict(meta["params"])
    merged = {**defaults, **(params or {})}
    constraints = meta.get("constraints", {})

    for key, default in defaults.items():
        if key not in merged:
            merged[key] = default

    for key, value in merged.items():
        if key not in defaults:
            raise ValueError(f"Unknown parameter: {key}")
        if not isinstance(value, (int, float)):
            raise ValueError(f"Parameter {key} must be numeric")
        if isinstance(default, int) and not float(value).is_integer():
            raise ValueError(f"Parameter {key} must be an integer")
        merged[key] = int(value) if isinstance(default, int) else float(value)

    for key, bounds in constraints.items():
        lo, hi = bounds
        if merged[key] < lo or merged[key] > hi:
            raise ValueError(f"Parameter {key} must be between {lo} and {hi}")

    if strategy_id in ("sma_crossover", "ema_crossover"):
        if merged["fast_period"] >= merged["slow_period"]:
            raise ValueError("fast_period must be less than slow_period")

    if strategy_id == "rsi_reversion" and merged["oversold"] >= merged["overbought"]:
        raise ValueError("oversold must be less than overbought")

    if strategy_id in ("stochastic_reversion", "mfi_reversion") and merged["oversold"] >= merged["overbought"]:
        raise ValueError("oversold must be less than overbought")

    return merged


def _validate_ensemble_params(params: dict[str, Any] | None) -> dict[str, Any]:
    defaults = dict(STRATEGY_CATALOG["strategy_ensemble"]["params"])
    merged = {**defaults, **(params or {})}

    combine_mode = merged.get("combine_mode", defaults["combine_mode"])
    if combine_mode not in COMBINE_MODES:
        raise ValueError("combine_mode must be unanimous, majority, or weighted")

    threshold = merged.get("threshold", defaults["threshold"])
    if not isinstance(threshold, (int, float)):
        raise ValueError("threshold must be numeric")
    threshold = float(threshold)
    lo, hi = STRATEGY_CATALOG["strategy_ensemble"]["constraints"]["threshold"]
    if threshold < lo or threshold > hi:
        raise ValueError(f"threshold must be between {lo} and {hi}")

    legs = merged.get("legs", defaults["legs"])
    if not isinstance(legs, list):
        raise ValueError("legs must be a list")
    if len(legs) < MIN_ENSEMBLE_LEGS or len(legs) > MAX_ENSEMBLE_LEGS:
        raise ValueError(f"ensemble requires between {MIN_ENSEMBLE_LEGS} and {MAX_ENSEMBLE_LEGS} legs")

    validated_legs: list[dict[str, Any]] = []
    for index, leg in enumerate(legs):
        if not isinstance(leg, dict):
            raise ValueError(f"leg {index} must be an object")
        strategy_id = leg.get("strategy_id")
        if strategy_id not in ENSEMBLE_LEG_STRATEGIES:
            raise ValueError(f"leg {index} strategy_id is not eligible for ensemble")
        weight = leg.get("weight", 1.0)
        if not isinstance(weight, (int, float)) or float(weight) <= 0:
            raise ValueError(f"leg {index} weight must be greater than 0")
        leg_params = _validate_scalar_params(strategy_id, leg.get("params"))
        leg_signal_tf = leg.get("signal_timeframe")
        if leg_signal_tf is not None:
            validate_timeframe(str(leg_signal_tf), f"leg {index} signal timeframe")
        validated_legs.append(
            {
                "strategy_id": strategy_id,
                "params": leg_params,
                "weight": float(weight),
                **({"signal_timeframe": str(leg_signal_tf)} if leg_signal_tf else {}),
            }
        )

    return {
        "combine_mode": combine_mode,
        "threshold": threshold,
        "legs": validated_legs,
    }


def validate_params(strategy_id: str, params: dict[str, Any] | None) -> dict[str, Any]:
    if strategy_id == "strategy_ensemble":
        return _validate_ensemble_params(params)
    return _validate_scalar_params(strategy_id, params)


def ensemble_min_bars(params: dict[str, Any]) -> int:
    return ensemble.ensemble_min_bars(params["legs"])


def get_signal_fn(strategy_id: str) -> SignalFn:
    return resolve_strategy(strategy_id)["signal_fn"]
