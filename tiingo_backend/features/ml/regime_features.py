"""Regime detection and dynamic indicator selection."""

from __future__ import annotations

from typing import Optional

INDICATOR_GROUPS: dict[str, list[str]] = {
    "momentum": ["ret_5", "ret_20", "ema20_dist", "ema50_dist", "ema20_ema50_spread"],
    "mean_reversion": ["rsi_14", "sma20_dist", "sma50_dist", "rsi_momentum"],
    "volatility": ["vol_20", "atr_14", "hl_range"],
}

DEFAULT_INDICATOR_GROUPS: tuple[str, ...] = tuple(INDICATOR_GROUPS.keys())

_REGIME_PREFERRED_GROUP = {
    "high_vol": "volatility",
    "low_vol": "mean_reversion",
    "mid_vol": "momentum",
}


def resolve_enabled_indicator_groups(params: dict) -> frozenset[str]:
    raw = params.get("indicator_groups")
    if not raw:
        return frozenset(DEFAULT_INDICATOR_GROUPS)
    if not isinstance(raw, list):
        raise ValueError("indicator_groups must be a list of group names")
    enabled = frozenset(str(item) for item in raw)
    unknown = enabled - set(INDICATOR_GROUPS)
    if unknown:
        supported = ", ".join(sorted(INDICATOR_GROUPS))
        raise ValueError(
            f"Unknown indicator_groups: {', '.join(sorted(unknown))}. Supported: {supported}",
        )
    if not enabled:
        raise ValueError("indicator_groups must contain at least one group")
    return enabled


def _preferred_group_for_regime(regime: str, enabled_groups: frozenset[str]) -> str:
    preferred = _REGIME_PREFERRED_GROUP.get(regime, "momentum")
    if preferred in enabled_groups:
        return preferred
    for fallback in ("momentum", "mean_reversion", "volatility"):
        if fallback in enabled_groups:
            return fallback
    return next(iter(enabled_groups))


def _feature_names_for_groups(enabled_groups: frozenset[str]) -> set[str]:
    names: set[str] = set()
    for group_id in enabled_groups:
        names.update(INDICATOR_GROUPS[group_id])
    return names


def trailing_volatility(closes: list[float], index: int, period: int = 20) -> Optional[float]:
    if index < period:
        return None
    rets = []
    for i in range(index - period + 1, index + 1):
        if closes[i - 1] == 0:
            continue
        rets.append((closes[i] / closes[i - 1]) - 1.0)
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    return var ** 0.5


def classify_regime(vol: float, low: float, high: float) -> str:
    if vol <= low:
        return "low_vol"
    if vol >= high:
        return "high_vol"
    return "mid_vol"


def regime_at_index(
    closes: list[float],
    index: int,
    *,
    period: int = 20,
    vol_low_pct: float = 0.33,
    vol_high_pct: float = 0.67,
) -> Optional[str]:
    vols: list[float] = []
    for i in range(period, len(closes)):
        v = trailing_volatility(closes, i, period)
        if v is not None:
            vols.append(v)
    current = trailing_volatility(closes, index, period)
    if current is None or not vols:
        return None
    sorted_vols = sorted(vols)
    n = len(sorted_vols)
    low = sorted_vols[int(n * vol_low_pct)]
    high = sorted_vols[int(n * vol_high_pct)]
    return classify_regime(current, low, high)


def select_features_for_regime(
    feature_names: list[str],
    importances: dict[str, float],
    regime: str,
    *,
    top_n: int = 5,
    enabled_groups: frozenset[str] | None = None,
) -> list[str]:
    groups = enabled_groups or frozenset(DEFAULT_INDICATOR_GROUPS)
    group_names = _feature_names_for_groups(groups)
    candidates = [f for f in feature_names if f in group_names]
    preferred_group = _preferred_group_for_regime(regime, groups)
    preferred = set(INDICATOR_GROUPS[preferred_group])
    candidates = [c for c in candidates if c in preferred] or candidates

    ranked = sorted(
        candidates,
        key=lambda name: importances.get(name, 0.0),
        reverse=True,
    )
    return ranked[:top_n]
