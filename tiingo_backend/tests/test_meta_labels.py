from datetime import datetime, timedelta, timezone

from features.ml.meta_label_events import build_event_mask
from features.ml.meta_labels import build_meta_labels, label_single_event


def _bar(index: int, close: float, high: float, low: float) -> dict:
    return {
        "time": datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(hours=index),
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1000.0,
    }


def test_label_single_event_success_before_stop():
    bars = [_bar(i, 100.0 + i * 0.1, 101.0 + i * 0.1, 99.0 + i * 0.1) for i in range(30)]
    bars[20]["high"] = 200.0
    label = label_single_event(
        bars,
        15,
        profit_atr_mult=2.0,
        stop_atr_mult=1.5,
        max_horizon_bars=10,
    )
    assert label == 1


def test_build_meta_labels_only_on_events():
    bars = []
    for i in range(60):
        close = 100.0 + (i * 0.5)
        bars.append(_bar(i, close, close + 1.0, close - 1.0))

    params = {"base_strategy_id": "crypto_trend_entry"}
    event_mask = build_event_mask(bars, params)
    labels = build_meta_labels(bars, event_mask, max_horizon_bars=12)
    assert len(labels) == len(bars)
    for index, is_event in enumerate(event_mask):
        if not is_event:
            assert labels[index] is None
