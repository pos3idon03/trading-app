from dataclasses import dataclass

from features.backtesting.bar_align import build_signal_index_map


@dataclass(frozen=True)
class MultiTimeframeContext:
    decision_timeframe: str
    decision_bars: list[dict]
    bars_by_timeframe: dict[str, list[dict]]
    signal_index_maps: dict[str, list[int]]
    standalone_signal_timeframe: str

    def bars_for(self, timeframe: str) -> list[dict]:
        return self.bars_by_timeframe[timeframe]

    def aligned_index(self, decision_index: int, signal_timeframe: str) -> int:
        mapping = self.signal_index_maps[signal_timeframe]
        return mapping[decision_index]


def build_multi_timeframe_context(
    *,
    decision_timeframe: str,
    decision_bars: list[dict],
    bars_by_timeframe: dict[str, list[dict]],
    standalone_signal_timeframe: str,
) -> MultiTimeframeContext:
    signal_maps: dict[str, list[int]] = {}
    for timeframe, bars in bars_by_timeframe.items():
        signal_maps[timeframe] = build_signal_index_map(decision_bars, bars)

    return MultiTimeframeContext(
        decision_timeframe=decision_timeframe,
        decision_bars=decision_bars,
        bars_by_timeframe=bars_by_timeframe,
        signal_index_maps=signal_maps,
        standalone_signal_timeframe=standalone_signal_timeframe,
    )
