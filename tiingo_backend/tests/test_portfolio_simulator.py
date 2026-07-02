from datetime import datetime, timezone

from features.backtesting.portfolio_simulator import (
    MultiAssetPortfolioState,
    buy_qty,
    mark_multi_equity,
    sell_qty,
)


def _bar(close: float) -> dict:
    return {
        "time": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
    }


def test_partial_buy_and_sell():
    state = MultiAssetPortfolioState(cash=10_000.0)
    bar = _bar(100.0)
    buy_qty(state, "AAPL", 50, 100.0, bar, commission_bps=0)
    equity, _ = mark_multi_equity(state, {"AAPL": 100.0}, 10_000.0)
    assert state.positions["AAPL"] == 50
    trades = []
    sell_qty(state, "AAPL", 50, 110.0, bar, 0, trades)
    assert state.positions.get("AAPL") is None
    assert len(trades) == 1
