import pytest

from features.ml.signals import count_signals, probabilities_to_signals


def test_probabilities_to_signals_threshold_mapping():
    signals = probabilities_to_signals(
        [None, 0.60, 0.50, 0.40],
        buy_threshold=0.55,
        sell_threshold=0.45,
    )
    assert signals == ["hold", "buy", "hold", "sell"]


def test_invalid_thresholds_raise():
    with pytest.raises(ValueError):
        probabilities_to_signals([0.5], buy_threshold=0.45, sell_threshold=0.55)


def test_count_signals():
    counts = count_signals(["buy", "hold", "sell", "buy"])
    assert counts == {"buy": 2, "sell": 1, "hold": 1}
