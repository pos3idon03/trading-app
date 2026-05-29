from datetime import datetime, timedelta, timezone

from features.ml.price_features import FEATURE_WARMUP_BARS, build_price_feature_matrix


def _bars(count: int, start_price: float = 100.0, step: float = 0.5) -> list[dict]:
    rows = []
    for i in range(count):
        price = start_price + (i * step)
        rows.append(
            {
                "time": datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price,
                "div_cash": 0,
                "split_factor": 1,
            }
        )
    return rows


def test_build_price_feature_matrix_aligns_with_bars():
    bars = _bars(250)
    names, rows = build_price_feature_matrix(bars)
    assert len(names) == 12
    assert len(rows) == len(bars)


def test_warmup_rows_are_none():
    bars = _bars(250)
    _, rows = build_price_feature_matrix(bars)
    for index in range(FEATURE_WARMUP_BARS):
        assert rows[index] is None


def test_features_use_only_past_data():
    bars = _bars(250)
    feature_names, rows = build_price_feature_matrix(bars)

    index = 70
    truncated_names, truncated_rows = build_price_feature_matrix(bars[: index + 1])
    assert truncated_rows[index] == rows[index]
    assert truncated_names == feature_names
