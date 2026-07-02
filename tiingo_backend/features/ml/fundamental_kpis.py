"""Derived valuation KPIs for ML fundamental features."""

from __future__ import annotations

from typing import Optional

from features.ml.asof_join import asof_observation_index, bar_dates_from_bars

PE_RATIO_COLUMN = "pe_ratio"


def _unique_quarterly_eps_values(observations: list[dict], obs_index: int) -> list[float]:
    visible = observations[: obs_index + 1]
    seen: set[str] = set()
    values: list[float] = []
    for obs in reversed(visible):
        period = obs.get("period") or ""
        if not period or period.startswith("FY-"):
            continue
        if period in seen:
            continue
        seen.add(period)
        values.append(float(obs["value"]))
        if len(values) == 4:
            break
    return list(reversed(values))


def compute_ttm_eps_at_index(observations: list[dict], obs_index: int | None) -> float | None:
    if obs_index is None:
        return None
    values = _unique_quarterly_eps_values(observations, obs_index)
    if len(values) < 4:
        return None
    return sum(values)


def build_pe_ratio_column(
    bars: list[dict],
    eps_observations: list[dict],
) -> list[Optional[float]]:
    if not bars:
        return []

    bar_dates = bar_dates_from_bars(bars)
    closes = [float(bar["close"]) for bar in bars]
    values: list[Optional[float]] = []
    for index, bar_date in enumerate(bar_dates):
        obs_index = asof_observation_index(eps_observations, bar_date)
        ttm_eps = compute_ttm_eps_at_index(eps_observations, obs_index)
        close = closes[index]
        if ttm_eps is None or ttm_eps <= 0 or close <= 0:
            values.append(None)
            continue
        values.append(close / ttm_eps)
    return values
