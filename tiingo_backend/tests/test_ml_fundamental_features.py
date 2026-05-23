from datetime import date, datetime, timedelta, timezone

from features.ml.fundamental_features import build_fundamental_feature_matrix


def _daily_bars(count: int, start: date) -> list[dict]:
    rows = []
    for i in range(count):
        rows.append(
            {
                "time": datetime.combine(
                    start + timedelta(days=i),
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                ),
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100 + i * 0.1,
            }
        )
    return rows


def _quarterly_rows(
    metric: str,
    reports: list[tuple[date, str, float]],
) -> list[dict]:
    return [
        {
            "time": datetime.combine(report_date, datetime.min.time(), tzinfo=timezone.utc),
            "metric_name": metric,
            "value": value,
            "period": period,
            "statement_type": "incomeStatement",
        }
        for report_date, period, value in reports
    ]


def test_report_not_visible_before_publication_date():
    pub = date(2024, 2, 15)
    bars = _daily_bars(5, start=date(2024, 2, 12))
    rows = _quarterly_rows(
        "revenue",
        [(pub, "2023-Q4", 1000.0)],
    )
    names, feature_rows, warnings = build_fundamental_feature_matrix(
        bars,
        {"revenue": rows},
        ["revenue"],
        "quarterly",
    )
    assert not warnings
    assert "revenue_level" in names
    # Feb 12-14: before publication
    assert feature_rows[0] is None
    assert feature_rows[1] is None
    assert feature_rows[2] is None
    # Feb 15+: report visible
    assert feature_rows[3] is not None
    assert feature_rows[3][0] == 1000.0


def test_forward_fill_stable_between_reports():
    bars = _daily_bars(150, start=date(2024, 1, 1))
    rows = _quarterly_rows(
        "revenue",
        [
            (date(2024, 2, 1), "2023-Q4", 100.0),
            (date(2024, 5, 1), "2024-Q1", 110.0),
        ],
    )
    _, feature_rows, _ = build_fundamental_feature_matrix(
        bars,
        {"revenue": rows},
        ["revenue"],
        "quarterly",
    )
    feb_levels = [row[0] for row in feature_rows if row and row[0] == 100.0]
    assert len(feb_levels) > 10
    may_levels = [row[0] for row in feature_rows if row and row[0] == 110.0]
    assert len(may_levels) > 10


def test_yoy_computed_from_visible_reports_only():
    bars = _daily_bars(1, start=date(2024, 5, 2))
    rows = _quarterly_rows(
        "revenue",
        [
            (date(2023, 5, 1), "2023-Q1", 90.0),
            (date(2024, 5, 1), "2024-Q1", 100.0),
        ],
    )
    names, feature_rows, _ = build_fundamental_feature_matrix(
        bars,
        {"revenue": rows},
        ["revenue"],
        "quarterly",
    )
    assert "revenue_yoy" in names
    assert feature_rows[0] is not None
    yoy_index = names.index("revenue_yoy")
    assert round(feature_rows[0][yoy_index], 4) == round((100 - 90) / 90, 4)


def test_missing_metric_emits_warning():
    bars = _daily_bars(10, start=date(2024, 1, 1))
    names, rows, warnings = build_fundamental_feature_matrix(bars, {}, ["revenue"])
    assert names == []
    assert all(row is None for row in rows)
    assert warnings


def test_column_names_include_derived_and_meta():
    bars = _daily_bars(30, start=date(2024, 3, 1))
    rows = _quarterly_rows(
        "roe",
        [
            (date(2023, 5, 1), "2023-Q1", 0.12),
            (date(2024, 5, 1), "2024-Q1", 0.15),
        ],
    )
    names, feature_rows, _ = build_fundamental_feature_matrix(
        bars,
        {"roe": rows},
        ["roe"],
        "quarterly",
    )
    assert names == [
        "roe_level",
        "roe_yoy",
        "roe_qoq",
        "roe_quarters_since_report",
    ]
    assert any(row is not None for row in feature_rows)
