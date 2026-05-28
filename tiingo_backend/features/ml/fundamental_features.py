from datetime import date
from typing import Optional

from features.market_data.fundamentals_growth import (
    _parse_period,
    _period_key,
    _prior_quarter,
)
from features.ml.asof_join import (
    asof_observation_index,
    bar_dates_from_bars,
    forward_fill_asof,
)

_DAYS_PER_QUARTER = 91.25


def _pct_change_decimal(current: float, reference: float) -> float | None:
    if reference == 0:
        return None
    return (current - reference) / reference


def _rows_to_observations(rows: list[dict]) -> list[dict]:
    observations: list[dict] = []
    for row in rows:
        obs_time = row["time"]
        obs_date = obs_time.date() if hasattr(obs_time, "date") else obs_time
        observations.append(
            {
                "obs_date": obs_date,
                "value": float(row["value"]),
                "period": row.get("period") or "",
            }
        )
    observations.sort(key=lambda item: item["obs_date"])
    return observations


def _period_value_map(visible: list[dict]) -> dict[str, float]:
    by_period: dict[str, float] = {}
    for obs in visible:
        period = obs.get("period") or ""
        if period:
            by_period[period] = obs["value"]
    return by_period


def _annual_reference_periods(period: str) -> tuple[str | None, str | None]:
    if not period.startswith("FY-"):
        return None, None
    try:
        year = int(period[3:])
    except ValueError:
        return None, None
    prior = f"FY-{year - 1}"
    return prior, prior


def _growth_for_period(
    period: str,
    by_period: dict[str, float],
    period_type: str,
) -> tuple[float | None, float | None]:
    if period_type == "annual":
        yoy_key, qoq_key = _annual_reference_periods(period)
        if not yoy_key:
            return None, None
        current = by_period.get(period)
        if current is None:
            return None, None
        yoy_ref = by_period.get(yoy_key)
        qoq_ref = by_period.get(qoq_key) if qoq_key else None
        yoy = _pct_change_decimal(current, yoy_ref) if yoy_ref is not None else None
        qoq = _pct_change_decimal(current, qoq_ref) if qoq_ref is not None else None
        return yoy, qoq

    parsed = _parse_period(period)
    if not parsed:
        return None, None
    year, quarter = parsed
    current = by_period.get(period)
    if current is None:
        return None, None

    yoy_key = _period_key(year - 1, quarter)
    pq_year, pq_quarter = _prior_quarter(year, quarter)
    qoq_key = _period_key(pq_year, pq_quarter)

    yoy_ref = by_period.get(yoy_key)
    qoq_ref = by_period.get(qoq_key)
    yoy = _pct_change_decimal(current, yoy_ref) if yoy_ref is not None else None
    qoq = _pct_change_decimal(current, qoq_ref) if qoq_ref is not None else None
    return yoy, qoq


def _build_metric_columns(
    bar_dates: list[date],
    metric_code: str,
    observations: list[dict],
    period_type: str,
) -> tuple[list[str], list[list[Optional[float]]]]:
    levels, days_since, _ = forward_fill_asof(bar_dates, observations, publication_lag_days=0)
    yoy_values: list[Optional[float]] = [None] * len(bar_dates)
    qoq_values: list[Optional[float]] = [None] * len(bar_dates)
    quarters_since: list[Optional[float]] = [None] * len(bar_dates)

    for index, bar_date in enumerate(bar_dates):
        obs_index = asof_observation_index(observations, bar_date)
        if obs_index is None:
            continue
        visible = observations[: obs_index + 1]
        period = observations[obs_index].get("period") or ""
        by_period = _period_value_map(visible)
        yoy, qoq = _growth_for_period(period, by_period, period_type)
        yoy_values[index] = yoy
        qoq_values[index] = qoq
        days = days_since[index]
        if days is not None:
            quarters_since[index] = round(days / _DAYS_PER_QUARTER, 2)

    names = [
        f"{metric_code}_level",
        f"{metric_code}_yoy",
        f"{metric_code}_qoq",
        f"{metric_code}_quarters_since_report",
    ]
    columns = [levels, yoy_values, qoq_values, quarters_since]
    return names, columns


def build_fundamental_feature_matrix(
    bars: list[dict],
    metric_data: dict[str, list[dict]],
    metric_codes: list[str],
    period_type: str = "quarterly",
) -> tuple[list[str], list[Optional[list[float]]], list[str]]:
    if not bars or not metric_codes:
        return [], [None] * len(bars), []

    bar_dates = bar_dates_from_bars(bars)
    feature_names: list[str] = []
    column_data: list[list[Optional[float]]] = []
    warnings: list[str] = []
    stale_fundamentals = False

    for metric_code in metric_codes:
        rows = metric_data.get(metric_code, [])
        if not rows:
            warnings.append(f"No observations for fundamental metric {metric_code}; columns omitted.")
            continue
        if not stale_fundamentals and not (rows[0].get("raw_data") or {}).get("as_reported"):
            stale_fundamentals = True
            warnings.append(
                "Fundamental rows may predate asReported ingestion; re-ingest fundamentals "
                "for point-in-time ML features.",
            )
        observations = _rows_to_observations(rows)
        names, columns = _build_metric_columns(bar_dates, metric_code, observations, period_type)
        feature_names.extend(names)
        column_data.extend(columns)

    if not feature_names:
        return [], [None] * len(bars), warnings

    rows: list[Optional[list[float]]] = []
    for row_index in range(len(bars)):
        row_values: list[float] = []
        row_complete = True
        for col_index, column in enumerate(column_data):
            value = column[row_index]
            if value is None:
                name = feature_names[col_index]
                if name.endswith("_yoy") or name.endswith("_qoq"):
                    row_values.append(0.0)
                    continue
                row_complete = False
                break
            row_values.append(float(value))
        rows.append(row_values if row_complete else None)

    return feature_names, rows, warnings
