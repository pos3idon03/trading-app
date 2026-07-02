from datetime import date, datetime, timezone

from features.ml.fundamental_features import build_fundamental_feature_matrix


def _bars(count: int = 3):
    return [
        {
            "time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "close": 100.0,
        }
        for _ in range(count)
    ]


def _metric_data():
    rows = [
        {
            "time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "value": 100.0,
            "period": "2024-Q1",
            "raw_data": {"as_reported": True},
        }
    ]
    return {"revenue": rows, "eps": rows}


def test_fundamental_features_mode_growth_only_omits_levels():
    names, rows, _ = build_fundamental_feature_matrix(
        _bars(),
        _metric_data(),
        ["revenue"],
        fundamental_features_mode="growth_only",
        include_valuation_kpis=False,
    )
    assert "revenue_level" not in names
    assert "revenue_yoy" in names
    assert rows[0] is not None


def test_include_valuation_kpis_adds_pe_ratio():
    names, _, _ = build_fundamental_feature_matrix(
        _bars(),
        _metric_data(),
        ["revenue", "eps"],
        include_valuation_kpis=True,
    )
    assert "pe_ratio" in names
