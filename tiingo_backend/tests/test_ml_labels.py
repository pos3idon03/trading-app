import pytest

from features.ml.labels import build_labels, build_ternary_labels, label_distribution


def _bars(closes: list[float]) -> list[dict]:
    return [{"close": price} for price in closes]


def test_forward_label_positive_when_price_rises():
    labels = build_labels(_bars([100, 101, 102, 103]), label_horizon=2, label_mode="binary")
    assert labels[0] == 1


def test_forward_label_negative_when_price_falls():
    labels = build_labels(_bars([100, 99, 98, 97]), label_horizon=2, label_mode="binary")
    assert labels[0] == 0


def test_tail_bars_have_no_label():
    labels = build_labels(_bars([100, 101, 102]), label_horizon=2, label_mode="binary")
    assert labels[1] is None
    assert labels[2] is None


def test_ternary_labels_assign_buy_sell_and_ranging():
    labels = build_ternary_labels(_bars([100, 110, 90, 100]), 1, 0.05)
    assert labels[0] == 2
    assert labels[1] == 1


def test_label_distribution_counts():
    labels = [0, 0, 1, 2, None]
    assert label_distribution(labels) == {"0": 2, "1": 1, "2": 1}


def test_forward_return_at_exposes_public_helper():
    from features.ml.labels import forward_return_at

    bars = [{"close": 100}, {"close": 110}]
    assert forward_return_at(bars, 0, 1) == pytest.approx(0.1)


def test_label_horizon_must_be_positive():
    with pytest.raises(ValueError):
        build_labels(_bars([100, 101]), label_horizon=0)


def test_meta_label_without_params_does_not_raise():
    closes = [100.0 + i * 0.05 for i in range(300)]
    bars = [
        {"time": f"2024-01-{idx:02d}", "open": c, "high": c + 1, "low": c - 1, "close": c}
        for idx, c in enumerate(closes, start=1)
    ]
    labels = build_labels(bars, label_horizon=5, label_mode="meta_label")
    assert len(labels) == len(bars)
