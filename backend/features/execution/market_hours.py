"""US equity regular trading hours guard for auto-trading."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_NY = ZoneInfo("America/New_York")
_RTH_OPEN = 9 * 60 + 30  # 09:30
_RTH_CLOSE = 16 * 60  # 16:00


def is_us_equity_rth_open(now: datetime | None = None) -> bool:
    """Return True during NYSE regular session (Mon–Fri 09:30–16:00 ET)."""
    dt = now or datetime.now(_NY)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_NY)
    else:
        dt = dt.astimezone(_NY)

    if dt.weekday() >= 5:
        return False

    minutes = dt.hour * 60 + dt.minute
    return _RTH_OPEN <= minutes < _RTH_CLOSE


def should_run_stock_stream(now: datetime | None = None) -> bool:
    """Return True when the Alpaca stock WebSocket should be active."""
    return is_us_equity_rth_open(now)


def should_skip_order_for_asset_type(asset_type: str) -> bool:
    """Stocks/ETFs only trade in RTH; crypto is 24/7."""
    return asset_type in ("stock", "equity", "etf")
