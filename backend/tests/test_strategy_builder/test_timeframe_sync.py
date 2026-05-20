"""Tests for per-attachment timeframe collection and sync."""
from features.strategy_builder.timeframe_sync import collect_attachment_timeframes


class TestCollectAttachmentTimeframes:
    def test_standalone_attachment(self):
        rows = [{"strategy_name": "rsi", "timeframe": "4h", "params": None}]
        assert collect_attachment_timeframes(rows) == ["4h"]

    def test_combo_includes_leg_timeframes(self):
        rows = [{
            "strategy_name": "combo:majority",
            "timeframe": "1h",
            "params": {
                "strategies": [
                    {"strategy_name": "rsi", "timeframe": "4h"},
                    {"strategy_name": "atr_trailing_stop", "timeframe": "30m"},
                ],
            },
        }]
        tfs = collect_attachment_timeframes(rows)
        assert "1h" in tfs
        assert "4h" in tfs
        assert "30m" in tfs
