"""Survivorship bias detection and warnings."""

from __future__ import annotations

from datetime import date, datetime, timezone


def _bar_date(bar: dict) -> date:
    t = bar["time"]
    if isinstance(t, datetime):
        dt = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        return dt.date()
    if isinstance(t, date):
        return t
    parsed = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    return parsed.date()


def build_survivorship_warnings(
    *,
    symbols: list[str],
    instruments: dict[str, dict],
    bars_by_symbol: dict[str, list[dict]],
    requested_end: date | None,
    active_only_filter: bool = False,
) -> list[str]:
    warnings: list[str] = []
    if active_only_filter:
        warnings.append(
            "Run uses active-only symbol filter; delisted names may be excluded."
        )

    for symbol in symbols:
        inst = instruments.get(symbol, {})
        bars = bars_by_symbol.get(symbol, [])
        if not bars:
            warnings.append(f"{symbol}: no bar data in window.")
            continue
        last_bar_date = _bar_date(bars[-1])
        if requested_end and last_bar_date < requested_end:
            reason = inst.get("delist_reason") or "unknown"
            warnings.append(
                f"{symbol}: bars end {last_bar_date.isoformat()} before "
                f"requested end ({reason}); forced liquidation applied."
            )
        if inst.get("delisted_at"):
            warnings.append(f"{symbol}: marked delisted ({inst.get('delist_reason')}).")
    return warnings


def delisted_settlement_prices(instruments: dict[str, dict]) -> dict[str, float]:
    prices: dict[str, float] = {}
    for symbol, inst in instruments.items():
        meta = inst.get("metadata") or {}
        price = meta.get("final_settlement_price")
        if price is not None:
            prices[symbol] = float(price)
    return prices
