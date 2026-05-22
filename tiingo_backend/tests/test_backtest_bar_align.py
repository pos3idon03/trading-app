from datetime import datetime, timedelta, timezone

from features.backtesting.bar_align import build_signal_index_map


def _bar(minute: int) -> dict:
    return {"time": datetime(2024, 1, 2, 9, minute, tzinfo=timezone.utc), "close": float(minute)}


def test_maps_decision_bars_to_last_closed_signal_bar():
    decision = [_bar(0), _bar(15), _bar(30)]
    signal = [_bar(0), _bar(5), _bar(10), _bar(15), _bar(20), _bar(25), _bar(30)]
    mapping = build_signal_index_map(decision, signal)
    assert mapping == [0, 3, 6]


def test_returns_negative_before_first_signal_bar():
    decision = [_bar(0)]
    signal = [_bar(15)]
    assert build_signal_index_map(decision, signal) == [-1]


def test_coarser_signal_timeframe():
    base = datetime(2024, 1, 2, 9, 0, tzinfo=timezone.utc)
    decision = [{"time": base + timedelta(minutes=15 * i), "close": i} for i in range(4)]
    signal = [{"time": base + timedelta(minutes=30 * i), "close": i} for i in range(3)]
    mapping = build_signal_index_map(decision, signal)
    assert mapping == [0, 0, 1, 1]
