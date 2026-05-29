from datetime import date, datetime, timedelta, timezone

from features.ml.liquidity_features import build_liquidity_feature_matrix


def _obs(obs_date: date, value: float) -> dict:
    return {"obs_date": obs_date, "value": value, "release_date": obs_date}


def test_build_liquidity_feature_matrix_net_liquidity():
    bars = [
        {"time": datetime(2024, 6, day, tzinfo=timezone.utc)}
        for day in range(1, 16)
    ]
    t10y2y_obs = [_obs(date(2024, 5, 25) + timedelta(days=i), 0.5 + i * 0.01) for i in range(20)]
    walcl_obs = [_obs(date(2024, 5, 25) + timedelta(days=i * 7), 8000.0 + i * 10) for i in range(5)]
    wtregen_obs = [_obs(date(2024, 5, 25) + timedelta(days=i * 7), 500.0 + i * 5) for i in range(5)]
    series_data = {
        "T10Y2Y": t10y2y_obs,
        "WALCL": walcl_obs,
        "WTREGEN": wtregen_obs,
    }
    names, rows, _warnings = build_liquidity_feature_matrix(
        bars,
        series_data,
        {"rates": 1},
    )
    assert "fed_net_liquidity" in names
    assert "t10y2y_level" in names
    assert rows[-1] is not None
    net_index = names.index("fed_net_liquidity")
    assert rows[-1][net_index] is not None
