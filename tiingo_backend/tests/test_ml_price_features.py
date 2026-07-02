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
                "volume": 1_000_000.0 + i * 10_000,
                "div_cash": 0,
                "split_factor": 1,
            }
        )
    return rows


def test_build_price_feature_matrix_aligns_with_bars():
    bars = _bars(250)
    names, rows = build_price_feature_matrix(bars)
    assert "volume_rel_20" in names
    assert "ema20_ema50_spread" in names
    assert "sma50_ema200_spread" in names
    assert "rsi_momentum" in names
    assert len(names) == 24
    assert len(rows) == len(bars)


def test_warmup_rows_are_none():
    bars = _bars(250)
    _, rows = build_price_feature_matrix(bars)
    for index in range(FEATURE_WARMUP_BARS):
        assert rows[index] is None


def test_custom_warmup_bars():
    bars = _bars(250)
    warmup = 200
    _, rows = build_price_feature_matrix(bars, warmup_bars=warmup)
    for index in range(warmup):
        assert rows[index] is None
    assert rows[warmup] is not None


def test_features_use_only_past_data():
    bars = _bars(250)
    feature_names, rows = build_price_feature_matrix(bars)

    index = 70
    truncated_names, truncated_rows = build_price_feature_matrix(bars[: index + 1])
    assert truncated_rows[index] == rows[index]
    assert truncated_names == feature_names


def test_volume_rel_20_in_feature_row():
    bars = _bars(250)
    names, rows = build_price_feature_matrix(bars)
    idx = names.index("volume_rel_20")
    row = rows[FEATURE_WARMUP_BARS]
    assert row is not None
    assert row[idx] > 0


def test_volume_rel_20_zero_when_no_volume():
    bars = _bars(250)
    for bar in bars:
        bar["volume"] = 0
    names, rows = build_price_feature_matrix(bars)
    idx = names.index("volume_rel_20")
    row = rows[FEATURE_WARMUP_BARS]
    assert row is not None
    assert row[idx] == 0.0
