from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dal import macro_dal
from features.fred.catalog import SERIES_CATALOG

_PERIOD_OFFSETS: dict[str, dict[str, int]] = {
    "Daily": {"1m": 21, "3m": 63, "6m": 126},
    "Weekly": {"1m": 4, "3m": 13, "6m": 26},
    "Monthly": {"1m": 1, "3m": 3, "6m": 6},
    "Quarterly": {"1m": 1, "3m": 1, "6m": 2},
}
_DEFAULT_OFFSETS = _PERIOD_OFFSETS["Monthly"]
_VALID_CATEGORIES = {
    "all", "growth", "labor", "inflation", "consumer", "rates", "housing", "energy", "goods",
}


def _offsets_for_frequency(frequency: str | None) -> dict[str, int]:
    if frequency and frequency in _PERIOD_OFFSETS:
        return _PERIOD_OFFSETS[frequency]
    return _DEFAULT_OFFSETS


def _pct_change(current: float, reference: float) -> float | None:
    if reference == 0:
        return None
    return round(((current - reference) / reference) * 100.0, 2)


def _change_from_offset(obs: list[dict], offset: int) -> float | None:
    if len(obs) <= offset:
        return None
    current = obs[-1]["value"]
    prior = obs[-(offset + 1)]["value"]
    if current is None or prior is None:
        return None
    return _pct_change(float(current), float(prior))


def _ytd_change(obs: list[dict]) -> float | None:
    if not obs:
        return None
    latest = obs[-1]
    if latest["value"] is None:
        return None
    year_start = date(latest["obs_date"].year, 1, 1)
    ref_value: float | None = None
    for row in obs:
        if row["obs_date"] >= year_start and row["value"] is not None:
            ref_value = float(row["value"])
            break
    if ref_value is None:
        return None
    return _pct_change(float(latest["value"]), ref_value)


def _ma_position(obs: list[dict], window: int) -> str:
    if len(obs) < window:
        return "—"
    window_obs = obs[-window:]
    values = [float(row["value"]) for row in window_obs if row["value"] is not None]
    if len(values) < window:
        return "—"
    latest = obs[-1]["value"]
    if latest is None:
        return "—"
    ma = sum(values) / len(values)
    if float(latest) > ma:
        return "Above"
    if float(latest) < ma:
        return "Below"
    return "At"


def _series_meta(series_id: str) -> dict:
    meta = SERIES_CATALOG.get(series_id, {})
    return {
        "series_id": series_id,
        "title": meta.get("title", series_id),
        "frequency": meta.get("frequency"),
        "category": meta.get("category", "general"),
    }


def _compute_row(obs: list[dict], meta: dict) -> dict:
    offsets = _offsets_for_frequency(meta.get("frequency"))
    return {
        **meta,
        "change_1m": _change_from_offset(obs, offsets["1m"]),
        "change_3m": _change_from_offset(obs, offsets["3m"]),
        "change_6m": _change_from_offset(obs, offsets["6m"]),
        "change_ytd": _ytd_change(obs),
        "ma50_position": _ma_position(obs, 50),
        "ma200_position": _ma_position(obs, 200),
    }


def _filter_series(category: str) -> list[dict]:
    rows = [_series_meta(series_id) for series_id in SERIES_CATALOG]
    if category == "all":
        return rows
    return [row for row in rows if row["category"] == category]


async def _load_observations(session: AsyncSession, series_id: str) -> list[dict]:
    obs = await macro_dal.get_observations(
        session,
        series_id,
        limit=250,
        order="desc",
    )
    return list(reversed(obs))


async def load_macro_overview(session: AsyncSession, category: str) -> dict:
    if category not in _VALID_CATEGORIES:
        raise ValueError(f"Invalid category: {category}")

    series_list = _filter_series(category)
    rows: list[dict] = []
    as_of: date | None = None

    for meta in series_list:
        obs = await _load_observations(session, meta["series_id"])
        if not obs:
            rows.append({**meta, "change_1m": None, "change_3m": None, "change_6m": None,
                         "change_ytd": None, "ma50_position": "—", "ma200_position": "—"})
            continue
        row = _compute_row(obs, meta)
        latest_date = obs[-1]["obs_date"]
        if as_of is None or latest_date > as_of:
            as_of = latest_date
        rows.append(row)

    return {"category": category, "as_of": as_of, "rows": rows}
