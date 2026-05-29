from datetime import datetime, timezone
from uuid import uuid4

import pytest

from features.execution.portfolio_metrics import (
    compute_closed_pnl_for_period,
    compute_open_period_pnl,
    compute_period_return_from_bars,
    compute_row_period_pl,
    resolve_portfolio_period,
)


def _bar(day: int, close: float) -> dict:
    return {
        "time": datetime(2026, 1, day, tzinfo=timezone.utc),
        "close": close,
    }


def _order(
    *,
    side: str,
    qty: float,
    price: float,
    filled_at: datetime,
    status: str = "filled",
) -> dict:
    return {
        "id": uuid4(),
        "side": side,
        "qty": qty,
        "filled_qty": qty,
        "filled_avg_price": price,
        "status": status,
        "submitted_at": filled_at,
        "filled_at": filled_at,
    }


def test_resolve_portfolio_period_defaults_to_ytd():
    start, end = resolve_portfolio_period(None, None)
    assert start.month == 1
    assert start.day == 1
    assert end >= start


def test_resolve_portfolio_period_rejects_invalid_range():
    start = datetime(2026, 5, 10, tzinfo=timezone.utc)
    end = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="start must be before"):
        resolve_portfolio_period(start, end)


def test_compute_closed_pnl_for_period_counts_sells_in_range():
    period_start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    period_end = datetime(2026, 5, 31, tzinfo=timezone.utc)
    orders = [
        _order(side="buy", qty=10, price=100, filled_at=datetime(2026, 4, 1, tzinfo=timezone.utc)),
        _order(side="sell", qty=10, price=110, filled_at=datetime(2026, 5, 15, tzinfo=timezone.utc)),
    ]
    result = compute_closed_pnl_for_period(orders, period_start, period_end)
    assert result.amount == 100
    assert result.pct == 10.0


def test_compute_closed_pnl_for_period_ignores_sells_outside_range():
    period_start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    period_end = datetime(2026, 5, 31, tzinfo=timezone.utc)
    orders = [
        _order(side="buy", qty=10, price=100, filled_at=datetime(2026, 4, 1, tzinfo=timezone.utc)),
        _order(side="sell", qty=10, price=110, filled_at=datetime(2026, 6, 1, tzinfo=timezone.utc)),
    ]
    result = compute_closed_pnl_for_period(orders, period_start, period_end)
    assert result.amount == 0
    assert result.pct is None


def test_compute_open_period_pnl_uses_start_prices():
    positions = [
        {
            "symbol": "AAPL",
            "qty": 10,
            "current_price": 110,
            "avg_entry_price": 100,
        }
    ]
    result = compute_open_period_pnl(positions, {"AAPL": 100})
    assert result.amount == 100
    assert result.pct == 10.0


def test_compute_row_period_pl():
    row = {"symbol": "MSFT", "qty": 5, "current_price": 420, "avg_entry_price": 400}
    assert compute_row_period_pl(row, {"MSFT": 400}) == 100


def test_compute_period_return_from_bars_uses_stored_closes():
    bars = [_bar(1, 100.0), _bar(2, 102.0), _bar(3, 105.0)]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 3, tzinfo=timezone.utc)
    assert compute_period_return_from_bars(bars, start, end) == 5.0


def test_compute_period_return_from_bars_handles_weekend_start_with_lookback_bar():
    bars = [_bar(1, 100.0), _bar(5, 110.0)]
    start = datetime(2026, 1, 3, tzinfo=timezone.utc)
    end = datetime(2026, 1, 5, tzinfo=timezone.utc)
    assert compute_period_return_from_bars(bars, start, end) == 10.0


@pytest.mark.asyncio
async def test_load_stored_etf_daily_bars_reads_ingested_eod_source(monkeypatch):
    from features.execution import portfolio_metrics as metrics

    async def fake_get_by_symbol(_session, symbol):
        assert symbol == "QQQ"
        return {"id": 42, "symbol": "QQQ"}

    captured: dict = {}

    async def fake_get_bars(_session, instrument_id, timeframe, **kwargs):
        captured.update(
            {
                "instrument_id": instrument_id,
                "timeframe": timeframe,
                **kwargs,
            }
        )
        if kwargs.get("source") == "tiingo_eod":
            return ([_bar(1, 400.0), _bar(2, 404.0)], "tiingo_eod")
        return ([], None)

    monkeypatch.setattr(metrics.instrument_dal, "get_by_symbol", fake_get_by_symbol)
    monkeypatch.setattr(metrics.ohlcv_dal, "get_bars", fake_get_bars)

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    bars = await metrics.load_stored_etf_daily_bars(None, "QQQ", start, end)

    assert captured["source"] == "tiingo_eod"
    assert captured["instrument_id"] == 42
    assert captured["timeframe"] == "1d"
    assert len(bars) == 2


@pytest.mark.asyncio
async def test_load_start_prices_uses_tail_bars_near_period_start(monkeypatch):
    from features.execution import portfolio_metrics as metrics

    async def fake_get_by_symbol(_session, symbol):
        return {"id": 7, "symbol": symbol}

    captured: dict = {}

    async def fake_get_bars(_session, instrument_id, timeframe, **kwargs):
        captured.update({"instrument_id": instrument_id, "timeframe": timeframe, **kwargs})
        if kwargs.get("fetch_tail"):
            return (
                [
                    _bar(1, 50.0),
                    _bar(2, 100.0),
                ],
                kwargs.get("source") or "tiingo_eod",
            )
        return ([], None)

    monkeypatch.setattr(metrics.instrument_dal, "get_by_symbol", fake_get_by_symbol)
    monkeypatch.setattr(metrics.ohlcv_dal, "get_bars", fake_get_bars)

    start = datetime(2026, 1, 2, tzinfo=timezone.utc)
    prices = await metrics.load_start_prices(None, {"AAPL"}, start)

    assert captured["fetch_tail"] is True
    assert captured["source"] == "tiingo_eod"
    assert captured["limit"] == metrics._START_PRICE_TAIL_LIMIT
    assert prices["AAPL"] == 100.0
