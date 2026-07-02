from datetime import date, datetime, timezone

from features.ml.fundamental_kpis import (
    PE_RATIO_COLUMN,
    build_pe_ratio_column,
    compute_ttm_eps_at_index,
)


def _eps_observations():
    quarters = [
        ("2023-Q1", 1.0),
        ("2023-Q2", 1.1),
        ("2023-Q3", 1.2),
        ("2023-Q4", 1.3),
        ("2024-Q1", 1.4),
    ]
    return [
        {"obs_date": date(2023, 4 + index, 1), "value": value, "period": period}
        for index, (period, value) in enumerate(quarters)
    ]


def test_compute_ttm_eps_requires_four_quarters():
    observations = _eps_observations()
    assert compute_ttm_eps_at_index(observations, 2) is None
    assert compute_ttm_eps_at_index(observations, 4) == 5.0


def test_build_pe_ratio_column_is_point_in_time():
    bars = [
        {
            "time": datetime(2024, 6, 1, tzinfo=timezone.utc),
            "close": 46.0,
        }
    ]
    pe_values = build_pe_ratio_column(bars, _eps_observations())
    assert len(pe_values) == 1
    assert pe_values[0] == 9.2
    assert PE_RATIO_COLUMN == "pe_ratio"
