from datetime import date

from features.ml.asof_join import forward_fill_asof


def _monthly_obs() -> list[dict]:
    return [
        {"obs_date": date(2024, 1, 31), "value": 100.0},
        {"obs_date": date(2024, 2, 29), "value": 102.0},
        {"obs_date": date(2024, 3, 31), "value": 104.0},
    ]


def test_forward_fill_uses_last_observation_on_or_before_bar_date():
    bar_dates = [date(2024, 2, 1), date(2024, 2, 15), date(2024, 3, 15)]
    values, days_since, _ = forward_fill_asof(bar_dates, _monthly_obs())
    assert values == [100.0, 100.0, 102.0]
    assert days_since == [1, 15, 15]


def test_forward_fill_does_not_use_future_observations():
    bar_dates = [date(2024, 1, 15)]
    values, _, _ = forward_fill_asof(bar_dates, _monthly_obs())
    assert values == [None]


def test_publication_lag_shifts_effective_lookup_date():
    bar_dates = [date(2024, 2, 5)]
    values, _, _ = forward_fill_asof(bar_dates, _monthly_obs(), publication_lag_days=10)
    assert values == [None]


def test_release_date_prevents_lookahead_before_announcement():
    cpi_obs = [
        {
            "obs_date": date(2024, 1, 31),
            "value": 100.0,
            "release_date": date(2024, 2, 28),
        },
        {
            "obs_date": date(2024, 2, 29),
            "value": 102.0,
            "release_date": date(2024, 3, 28),
        },
    ]
    before_release, _, _ = forward_fill_asof([date(2024, 2, 15)], cpi_obs)
    assert before_release == [None]

    after_release, days_since, warnings = forward_fill_asof([date(2024, 2, 28)], cpi_obs)
    assert after_release == [100.0]
    assert days_since == [0]
    assert warnings == []
