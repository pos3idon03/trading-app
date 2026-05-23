from datetime import date, datetime, timedelta, timezone

from features.ml.assembler import assemble_feature_matrix
from features.ml.macro_features import build_macro_feature_matrix
from features.ml.price_features import FEATURE_NAMES, build_price_feature_matrix


def _daily_bars(count: int, start: date | None = None) -> list[dict]:
    base = start or date(2024, 1, 1)
    rows = []
    for i in range(count):
        rows.append(
            {
                "time": datetime.combine(base + timedelta(days=i), datetime.min.time(), tzinfo=timezone.utc),
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100 + (i * 0.1),
            }
        )
    return rows


def _daily_obs(count: int, start: date) -> list[dict]:
    return [
        {"obs_date": start + timedelta(days=i), "value": 4.0 + (i * 0.01)}
        for i in range(count)
    ]


def test_prices_macro_produces_wider_feature_matrix():
    bars = _daily_bars(80)
    obs = _daily_obs(120, date(2023, 9, 1))
    names, rows, warnings = build_macro_feature_matrix(
        bars,
        {"DFF": obs},
        ["DFF"],
    )
    assert "DFF_level" in names
    assert "DFF_chg_1m" in names
    assert "DFF_days_since_update" in names
    assert len(names) == 4
    assert all(row is not None for row in rows)


def test_missing_series_emits_warning_and_omits_columns():
    bars = _daily_bars(10)
    names, rows, warnings = build_macro_feature_matrix(bars, {}, ["DFF"])
    assert names == []
    assert all(row is None for row in rows)
    assert warnings


def test_assembler_prices_macro_wider_than_prices_only():
    bars = _daily_bars(80)
    obs = _daily_obs(120, date(2023, 9, 1))
    price_names, price_rows = build_price_feature_matrix(bars)
    macro_names, macro_rows, _ = build_macro_feature_matrix(bars, {"DFF": obs}, ["DFF"])
    only_names, _ = assemble_feature_matrix(
        "prices_only",
        price_names,
        price_rows,
        [],
        [],
    )
    combined_names, _ = assemble_feature_matrix(
        "prices_macro",
        price_names,
        price_rows,
        macro_names,
        macro_rows,
    )
    assert len(combined_names) > len(only_names)
    assert len(combined_names) == len(FEATURE_NAMES) + len(macro_names)
