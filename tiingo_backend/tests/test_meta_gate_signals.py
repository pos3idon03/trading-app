from features.ml.signals import meta_gate_signals


def test_meta_gate_signals_buy_only_when_event_and_threshold():
    event_mask = [False, True, True, False]
    probabilities = [None, 0.7, 0.4, 0.9]
    signals = meta_gate_signals(event_mask, probabilities, 0.65)
    assert signals == ["hold", "buy", "hold", "hold"]
