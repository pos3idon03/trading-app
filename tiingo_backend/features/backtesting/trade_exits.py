"""Trade exit rules for signal backtests (max-hold, ATR brackets)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from features.backtesting.indicators import compute_atr

ExitPolicy = Literal["signal_only", "label_horizon", "atr_bracket", "combined"]
IntrabarExit = Literal["stop", "profit"]

SUPPORTED_EXIT_POLICIES = frozenset(
    {"signal_only", "label_horizon", "atr_bracket", "combined"},
)


@dataclass(frozen=True)
class TradeExitConfig:
    policy: ExitPolicy
    max_hold_bars: int
    profit_atr_mult: float
    stop_atr_mult: float
    atr_period: int

    def is_active(self) -> bool:
        return self.policy != "signal_only"


@dataclass(frozen=True)
class PositionExitDecision:
    fill_price: float
    reason: str


def intrabar_long_exit(
    high: float,
    low: float,
    *,
    profit_level: float,
    stop_level: float,
) -> IntrabarExit | None:
    if low <= stop_level:
        return "stop"
    if high >= profit_level:
        return "profit"
    return None


def atr_bracket_levels(
    entry_price: float,
    atr: float,
    *,
    profit_atr_mult: float,
    stop_atr_mult: float,
) -> tuple[float, float]:
    return (
        entry_price + profit_atr_mult * atr,
        entry_price - stop_atr_mult * atr,
    )


def atr_at_bar_index(
    bars: list[dict],
    index: int,
    atr_period: int,
) -> float | None:
    if index < 0 or index >= len(bars):
        return None
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    closes = [float(b["close"]) for b in bars]
    atr_series = compute_atr(highs, lows, closes, atr_period)
    value = atr_series[index]
    if value is None or value <= 0:
        return None
    return float(value)


def default_exit_policy_for_label_mode(label_mode: str) -> ExitPolicy:
    if label_mode == "meta_label":
        return "atr_bracket"
    return "label_horizon"


def resolve_trade_exit_config(params: dict[str, Any]) -> TradeExitConfig:
    label_mode = str(params.get("label_mode") or "binary")
    policy = str(params.get("exit_policy") or "").strip()
    if not policy:
        policy = default_exit_policy_for_label_mode(label_mode)
    if policy not in SUPPORTED_EXIT_POLICIES:
        raise ValueError(
            f"exit_policy must be one of {sorted(SUPPORTED_EXIT_POLICIES)}",
        )

    label_horizon = int(params.get("label_horizon", 5))
    max_horizon = int(params.get("max_horizon_bars", 48))
    if params.get("max_hold_bars") is not None:
        max_hold = int(params["max_hold_bars"])
    elif label_mode == "meta_label":
        max_hold = max_horizon
    else:
        max_hold = label_horizon

    return TradeExitConfig(
        policy=policy,  # type: ignore[arg-type]
        max_hold_bars=max(1, max_hold),
        profit_atr_mult=float(params.get("profit_atr_mult", 2.0)),
        stop_atr_mult=float(params.get("stop_atr_mult", 1.5)),
        atr_period=int(params.get("atr_period", 14)),
    )


def _uses_atr(policy: ExitPolicy) -> bool:
    return policy in ("atr_bracket", "combined")


def _uses_max_hold(policy: ExitPolicy) -> bool:
    return policy in ("label_horizon", "combined")


def evaluate_position_exit(
    *,
    bar_index: int,
    bar: dict,
    entry_bar_index: int,
    entry_price: float,
    bars: list[dict],
    config: TradeExitConfig,
    profit_level: float | None = None,
    stop_level: float | None = None,
) -> PositionExitDecision | None:
    if not config.is_active() or entry_price <= 0:
        return None

    bars_held = bar_index - entry_bar_index
    open_price = float(bar["open"])

    if _uses_max_hold(config.policy) and bars_held >= config.max_hold_bars:
        return PositionExitDecision(fill_price=open_price, reason="max_hold")

    if not _uses_atr(config.policy):
        return None

    if profit_level is None or stop_level is None:
        atr = atr_at_bar_index(bars, entry_bar_index, config.atr_period)
        if atr is None:
            return None
        profit_level, stop_level = atr_bracket_levels(
            entry_price,
            atr,
            profit_atr_mult=config.profit_atr_mult,
            stop_atr_mult=config.stop_atr_mult,
        )

    hit = intrabar_long_exit(
        float(bar["high"]),
        float(bar["low"]),
        profit_level=profit_level,
        stop_level=stop_level,
    )
    if hit == "stop":
        return PositionExitDecision(fill_price=stop_level, reason="stop_atr")
    if hit == "profit":
        return PositionExitDecision(fill_price=profit_level, reason="profit_atr")
    return None


def cache_bracket_levels(
    bars: list[dict],
    entry_bar_index: int,
    entry_price: float,
    config: TradeExitConfig,
) -> tuple[float, float] | None:
    if not _uses_atr(config.policy):
        return None
    atr = atr_at_bar_index(bars, entry_bar_index, config.atr_period)
    if atr is None:
        return None
    profit_level, stop_level = atr_bracket_levels(
        entry_price,
        atr,
        profit_atr_mult=config.profit_atr_mult,
        stop_atr_mult=config.stop_atr_mult,
    )
    return profit_level, stop_level
