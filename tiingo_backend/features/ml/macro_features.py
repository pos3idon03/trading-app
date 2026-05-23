from datetime import date
from typing import Optional

from features.fred.catalog import SERIES_CATALOG
from features.ml.asof_join import (
    _lookup_date,
    asof_observation_index,
    bar_dates_from_bars,
    forward_fill_asof,
)

_PERIOD_OFFSETS: dict[str, dict[str, int]] = {
    "Daily": {"1m": 21, "3m": 63},
    "Weekly": {"1m": 4, "3m": 13},
    "Monthly": {"1m": 1, "3m": 3},
    "Quarterly": {"1m": 1, "3m": 1},
}
_DEFAULT_OFFSETS = _PERIOD_OFFSETS["Monthly"]
_CHANGE_WINDOWS = ("1m", "3m")


def _offsets_for_frequency(frequency: str | None) -> dict[str, int]:
    if frequency and frequency in _PERIOD_OFFSETS:
        return _PERIOD_OFFSETS[frequency]
    return _DEFAULT_OFFSETS


def _pct_change(current: float, reference: float) -> float | None:
    if reference == 0:
        return None
    return (current - reference) / reference


def _change_at_index(
    observations: list[dict],
    obs_index: int | None,
    offset: int,
) -> float | None:
    if obs_index is None or obs_index < offset:
        return None
    current = observations[obs_index]["value"]
    prior = observations[obs_index - offset]["value"]
    if current is None or prior is None:
        return None
    return _pct_change(float(current), float(prior))


def _series_lag(
    series_id: str,
    publication_lag_days: dict[str, int] | None,
) -> int:
    if not publication_lag_days:
        return 0
    category = SERIES_CATALOG.get(series_id, {}).get("category")
    if category and category in publication_lag_days:
        return int(publication_lag_days[category])
    return 0


def _build_series_columns(
    bar_dates: list[date],
    series_id: str,
    observations: list[dict],
    publication_lag_days: dict[str, int] | None,
) -> tuple[list[str], list[list[Optional[float]]], list[str]]:
    frequency = SERIES_CATALOG.get(series_id, {}).get("frequency")
    offsets = _offsets_for_frequency(frequency)
    lag = _series_lag(series_id, publication_lag_days)

    levels, days_since, join_warnings = forward_fill_asof(bar_dates, observations, lag)
    change_cols: dict[str, list[Optional[float]]] = {
        window: [None] * len(bar_dates) for window in _CHANGE_WINDOWS
    }

    for index, bar_date in enumerate(bar_dates):
        obs_index = asof_observation_index(
            observations,
            _lookup_date(bar_date, lag),
            lag,
        )
        if obs_index is None:
            continue
        for window in _CHANGE_WINDOWS:
            change_cols[window][index] = _change_at_index(
                observations,
                obs_index,
                offsets[window],
            )

    names = [
        f"{series_id}_level",
        f"{series_id}_chg_1m",
        f"{series_id}_chg_3m",
        f"{series_id}_days_since_update",
    ]
    columns = [
        levels,
        change_cols["1m"],
        change_cols["3m"],
        [float(d) if d is not None else None for d in days_since],
    ]
    return names, columns, join_warnings


def build_macro_feature_matrix(
    bars: list[dict],
    series_data: dict[str, list[dict]],
    series_ids: list[str],
    publication_lag_days: dict[str, int] | None = None,
) -> tuple[list[str], list[Optional[list[float]]], list[str]]:
    if not bars or not series_ids:
        return [], [None] * len(bars), []

    bar_dates = bar_dates_from_bars(bars)
    feature_names: list[str] = []
    column_data: list[list[Optional[float]]] = []
    warnings: list[str] = []

    for series_id in series_ids:
        observations = series_data.get(series_id, [])
        if not observations:
            warnings.append(f"No observations for macro series {series_id}; columns omitted.")
            continue
        names, columns, join_warnings = _build_series_columns(
            bar_dates,
            series_id,
            observations,
            publication_lag_days,
        )
        for warning in join_warnings:
            warnings.append(f"{series_id}: {warning}")
        feature_names.extend(names)
        column_data.extend(columns)

    if not feature_names:
        return [], [None] * len(bars), warnings

    rows: list[Optional[list[float]]] = []
    for row_index in range(len(bars)):
        row_values: list[float] = []
        for column in column_data:
            value = column[row_index]
            row_values.append(0.0 if value is None else float(value))
        rows.append(row_values)

    return feature_names, rows, warnings
