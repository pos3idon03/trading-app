from datetime import datetime, timezone

import pytest

from features.backtesting.simulator import (
    PortfolioState,
    apply_corporate_actions,
    buy_all_in,
    mark_equity,
    sell_all,
)


def _bar(day: int, open_: float, close: float, div_cash: float = 0, split_factor: float = 1) -> dict:
    return {
        "time": datetime(2024, 1, day, tzinfo=timezone.utc),
        "open": open_,
        "high": max(open_, close),
        "low": min(open_, close),
        "close": close,
        "div_cash": div_cash,
        "split_factor": split_factor,
    }


def test_buy_all_in_uses_cash_minus_commission():
    state = PortfolioState(cash=1000.0)
    bar = _bar(1, 100.0, 100.0)
    buy_all_in(state, 100.0, bar, commission_bps=10.0)
    assert state.shares == pytest.approx(9.9900099, rel=1e-4)
    assert state.entry_price == 100.0
    assert state.entry_date == "2024-01-01T00:00:00Z"


def test_apply_corporate_actions_is_noop_for_splits():
    state = PortfolioState(cash=0.0, shares=10.0)
    apply_corporate_actions(state, _bar(2, 50.0, 50.0, split_factor=2.0))
    assert state.shares == pytest.approx(10.0)


def test_apply_corporate_actions_is_noop_for_dividends():
    state = PortfolioState(cash=100.0, shares=10.0)
    apply_corporate_actions(state, _bar(2, 100.0, 100.0, div_cash=1.5))
    assert state.cash == pytest.approx(100.0)


def test_sell_all_records_trade():
    state = PortfolioState(cash=0.0, shares=10.0, entry_price=100.0, entry_date="2024-01-01T00:00:00Z")
    trades = []
    sell_all(state, 110.0, _bar(2, 110.0, 110.0), commission_bps=0.0, trades=trades)
    assert len(trades) == 1
    assert trades[0].pnl == pytest.approx(100.0)
    assert state.shares == 0.0


def test_mark_equity_tracks_drawdown():
    state = PortfolioState(cash=0.0, shares=10.0)
    equity, drawdown = mark_equity(state, _bar(1, 100.0, 90.0), peak_equity=1000.0)
    assert equity == pytest.approx(900.0)
    assert drawdown == pytest.approx(-10.0)
