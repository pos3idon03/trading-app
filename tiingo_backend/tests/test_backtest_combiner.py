import pytest

from features.backtesting.combiner import combine_signals


def test_unanimous_buy_and_sell():
    assert combine_signals(["buy", "buy"], [1.0, 1.0], "unanimous", 0.5) == "buy"
    assert combine_signals(["sell", "sell"], [1.0, 1.0], "unanimous", 0.5) == "sell"


def test_unanimous_mixed_signals_hold():
    assert combine_signals(["buy", "sell"], [1.0, 1.0], "unanimous", 0.5) == "hold"
    assert combine_signals(["buy", "hold"], [1.0, 1.0], "unanimous", 0.5) == "hold"


def test_majority_strict_majority():
    assert combine_signals(["buy", "buy", "sell"], [1, 1, 1], "majority", 0.5) == "buy"
    assert combine_signals(["sell", "sell", "buy"], [1, 1, 1], "majority", 0.5) == "sell"


def test_majority_two_leg_tie_holds():
    assert combine_signals(["buy", "sell"], [1.0, 1.0], "majority", 0.5) == "hold"


def test_weighted_net_score_threshold():
    assert combine_signals(["buy", "buy", "hold"], [1, 1, 1], "weighted", 0.5) == "buy"
    assert combine_signals(["sell", "sell", "hold"], [1, 1, 1], "weighted", 0.5) == "sell"


def test_weighted_respects_leg_weights():
    assert combine_signals(["buy", "sell"], [3.0, 1.0], "weighted", 0.5) == "buy"
    assert combine_signals(["buy", "sell"], [1.0, 3.0], "weighted", 0.5) == "sell"


def test_weighted_dead_zone_holds():
    assert combine_signals(["buy", "sell"], [1.0, 1.0], "weighted", 0.5) == "hold"


def test_empty_signals_hold():
    assert combine_signals([], [], "majority", 0.5) == "hold"


def test_unknown_mode_raises():
    with pytest.raises(ValueError, match="Unknown combine mode"):
        combine_signals(["buy"], [1.0], "invalid", 0.5)
