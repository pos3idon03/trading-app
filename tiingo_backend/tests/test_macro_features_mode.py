from datetime import date

from features.ml.macro_features import build_macro_feature_matrix


def _bars(count: int) -> list[dict]:
    return [{"time": date(2024, 1, 1)} for _ in range(count)]


def _series_data() -> dict[str, list[dict]]:
    return {
        "CPIAUCSL": [
            {"obs_date": date(2024, 1, 1), "value": 100.0, "release_date": date(2024, 1, 15)},
            {"obs_date": date(2024, 2, 1), "value": 101.0, "release_date": date(2024, 2, 15)},
        ]
    }


def test_macro_features_mode_full_includes_level():
    names, rows, _ = build_macro_feature_matrix(
        _bars(3),
        _series_data(),
        ["CPIAUCSL"],
        macro_features_mode="full",
    )
    assert "CPIAUCSL_level" in names
    assert rows[2] is not None


def test_macro_features_mode_changes_only_omits_level():
    names, rows, _ = build_macro_feature_matrix(
        _bars(3),
        _series_data(),
        ["CPIAUCSL"],
        macro_features_mode="changes_only",
    )
    assert "CPIAUCSL_level" not in names
    assert "CPIAUCSL_chg_1m" in names
    assert rows[2] is not None
