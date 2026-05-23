from datetime import date, timedelta


def bar_dates_from_bars(bars: list[dict]) -> list[date]:
    dates: list[date] = []
    for bar in bars:
        bar_time = bar["time"]
        if isinstance(bar_time, date) and not hasattr(bar_time, "hour"):
            dates.append(bar_time)
        else:
            dates.append(bar_time.date() if hasattr(bar_time, "date") else bar_time)
    return dates


def _lookup_date(bar_date: date, publication_lag_days: int) -> date:
    if publication_lag_days <= 0:
        return bar_date
    return bar_date - timedelta(days=publication_lag_days)


def _effective_join_date(observation: dict, publication_lag_days: int) -> date:
    release_date = observation.get("release_date")
    if release_date is not None:
        return release_date
    obs_date = observation["obs_date"]
    if publication_lag_days <= 0:
        return obs_date
    return obs_date + timedelta(days=publication_lag_days)


def forward_fill_asof(
    bar_dates: list[date],
    observations: list[dict],
    publication_lag_days: int = 0,
) -> tuple[list[float | None], list[int | None], list[str]]:
    if not bar_dates:
        return [], [], []

    values: list[float | None] = []
    days_since: list[int | None] = []
    warnings: list[str] = []
    obs_index = 0
    last_value: float | None = None
    last_join_date: date | None = None
    obs_len = len(observations)
    missing_release = any(obs.get("release_date") is None for obs in observations)

    if missing_release and publication_lag_days <= 0:
        warnings.append(
            "Some macro observations lack release_date; using obs_date (possible look-ahead bias).",
        )

    for bar_date in bar_dates:
        lookup = _lookup_date(bar_date, publication_lag_days)
        while obs_index < obs_len:
            join_date = _effective_join_date(observations[obs_index], publication_lag_days)
            if join_date <= lookup:
                raw = observations[obs_index]["value"]
                if raw is not None:
                    last_value = float(raw)
                    last_join_date = join_date
                obs_index += 1
            else:
                break

        values.append(last_value)
        if last_join_date is None:
            days_since.append(None)
        else:
            days_since.append((bar_date - last_join_date).days)

    return values, days_since, warnings


def asof_observation_index(
    observations: list[dict],
    lookup_date: date,
    publication_lag_days: int = 0,
) -> int | None:
    last_index: int | None = None
    for index, row in enumerate(observations):
        join_date = _effective_join_date(row, publication_lag_days)
        if join_date <= lookup_date:
            last_index = index
        else:
            break
    return last_index
