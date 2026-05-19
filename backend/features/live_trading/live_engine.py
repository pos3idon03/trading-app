"""Shared live-trading engine singleton (resampler)."""
from __future__ import annotations

from features.live_trading.resampler import ResamplingEngine

_resampler: ResamplingEngine | None = None
_persistence_registered = False


def get_resampler() -> ResamplingEngine:
    """Return the process-wide resampling engine, registering persistence once."""
    global _resampler, _persistence_registered
    if _resampler is None:
        _resampler = ResamplingEngine()
    if not _persistence_registered:
        from features.live_trading.bar_persistence import register_bar_persistence

        register_bar_persistence(_resampler)
        _persistence_registered = True
    return _resampler
