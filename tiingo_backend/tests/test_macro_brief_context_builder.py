from datetime import date

from features.agents.macro_crew.context_builder import build_macro_context, rows_fingerprint


def _sample_overview() -> dict:
    return {
        "category": "all",
        "as_of": date(2024, 6, 1),
        "rows": [
            {
                "series_id": "UNRATE",
                "title": "Unemployment Rate",
                "category": "labor",
                "frequency": "Monthly",
                "change_1m": 0.1,
                "change_3m": 0.2,
                "change_6m": 0.3,
                "change_ytd": 0.4,
                "ma50_position": "Above",
                "ma200_position": "Below",
            },
            {
                "series_id": "CPIAUCSL",
                "title": "CPI All Urban Consumers",
                "category": "inflation",
                "frequency": "Monthly",
                "change_1m": None,
                "change_3m": 1.1,
                "change_6m": 2.0,
                "change_ytd": 2.5,
                "ma50_position": "At",
                "ma200_position": "Above",
            },
        ],
    }


def test_build_macro_context_serializes_rows():
    ctx = build_macro_context(_sample_overview())
    assert ctx["as_of"] == "2024-06-01"
    assert ctx["series_count"] == 2
    assert ctx["series"][0]["series_id"] == "UNRATE"
    assert ctx["series"][0]["trends"]["change_1m"] == "+0.10%"
    assert ctx["series"][0]["ma50_position"] == "Above"
    assert ctx["series"][1]["trends"]["change_1m"] is None


def test_rows_fingerprint_is_stable():
    overview = _sample_overview()
    assert rows_fingerprint(overview) == rows_fingerprint(overview)


def test_rows_fingerprint_changes_when_data_changes():
    overview = _sample_overview()
    other = _sample_overview()
    other["rows"][0]["change_1m"] = 0.5
    assert rows_fingerprint(overview) != rows_fingerprint(other)
