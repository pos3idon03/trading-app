from datetime import date
from typing import Optional

from features.ml.asof_join import (
    _lookup_date,
    asof_observation_index,
    bar_dates_from_bars,
    forward_fill_asof,
)

_LIQUIDITY_SERIES = frozenset({"WALCL", "WTREGEN", "T10Y2Y"})
_T10Y2Y_CHG_OFFSET = 5
_NET_LIQ_ROC_OFFSET = 30


def _pct_change(current: float, reference: float) -> float | None:
    if reference == 0:
        return None
    return (current - reference) / reference


def _level_series(
    bar_dates: list[date],
    observations: list[dict],
    publication_lag_days: int,
) -> list[Optional[float]]:
    levels, _, _ = forward_fill_asof(bar_dates, observations, publication_lag_days)
    return levels


def _roc_at_index(
    levels: list[Optional[float]],
    index: int,
    offset: int,
) -> Optional[float]:
    if index < offset:
        return None
    current = levels[index]
    prior = levels[index - offset]
    if current is None or prior is None:
        return None
    return _pct_change(float(current), float(prior))


def _t10y2y_chg_5d(
    bar_dates: list[date],
    observations: list[dict],
    publication_lag_days: int,
) -> list[Optional[float]]:
    levels = _level_series(bar_dates, observations, publication_lag_days)
    return [_roc_at_index(levels, index, _T10Y2Y_CHG_OFFSET) for index in range(len(levels))]


def _net_liquidity_levels(
    bar_dates: list[date],
    walcl: list[dict],
    wtregen: list[dict],
    publication_lag_days: int,
) -> list[Optional[float]]:
    walcl_levels = _level_series(bar_dates, walcl, publication_lag_days)
    tga_levels = _level_series(bar_dates, wtregen, publication_lag_days)
    net: list[Optional[float]] = []
    for walcl_level, tga_level in zip(walcl_levels, tga_levels):
        if walcl_level is None or tga_level is None:
            net.append(None)
            continue
        net.append(float(walcl_level) - float(tga_level))
    return net


def build_liquidity_feature_matrix(
    bars: list[dict],
    series_data: dict[str, list[dict]],
    publication_lag_days: dict[str, int] | None = None,
) -> tuple[list[str], list[Optional[list[float]]], list[str]]:
    if not bars:
        return [], [], []

    lag_map = publication_lag_days or {}
    rates_lag = int(lag_map.get("rates", 1)) if isinstance(lag_map, dict) else 1
    bar_dates = bar_dates_from_bars(bars)
    warnings: list[str] = []
    columns: dict[str, list[Optional[float]]] = {}

    t10y2y_obs = series_data.get("T10Y2Y", [])
    if t10y2y_obs:
        t10_levels = _level_series(bar_dates, t10y2y_obs, rates_lag)
        columns["t10y2y_level"] = [float(v) if v is not None else None for v in t10_levels]
        columns["t10y2y_chg_5d"] = _t10y2y_chg_5d(bar_dates, t10y2y_obs, rates_lag)
    else:
        warnings.append("T10Y2Y not available; liquidity spread features omitted.")

    walcl_obs = series_data.get("WALCL", [])
    wtregen_obs = series_data.get("WTREGEN", [])
    if walcl_obs and wtregen_obs:
        net_levels = _net_liquidity_levels(bar_dates, walcl_obs, wtregen_obs, rates_lag)
        columns["fed_net_liquidity"] = net_levels
        columns["fed_net_liquidity_roc_30d"] = [
            _roc_at_index(net_levels, index, _NET_LIQ_ROC_OFFSET)
            for index in range(len(net_levels))
        ]
    else:
        warnings.append("WALCL and/or WTREGEN missing; net liquidity features omitted.")

    if not columns:
        return [], [None] * len(bars), warnings

    feature_names = list(columns.keys())
    rows: list[Optional[list[float]]] = []
    optional_zeros = {"t10y2y_chg_5d", "fed_net_liquidity_roc_30d"}
    for row_index in range(len(bars)):
        values: list[float] = []
        row_complete = True
        for name in feature_names:
            value = columns[name][row_index]
            if value is None:
                if name in optional_zeros:
                    values.append(0.0)
                    continue
                row_complete = False
                break
            values.append(float(value))
        rows.append(values if row_complete else None)

    return feature_names, rows, warnings


def liquidity_series_requested(series_ids: list[str]) -> bool:
    return bool(_LIQUIDITY_SERIES.intersection(series_ids))
