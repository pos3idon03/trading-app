from dataclasses import replace

import pandas as pd
import pytest

from orderflow import engine, synthetic
from orderflow.config import BacktestConfig, Config, ProfileConfig, StrategyConfig

NO_COSTS = Config(profile=ProfileConfig(bin_size=5), backtest=BacktestConfig(fee_bps=0, slippage_bps=0))


@pytest.fixture(scope="module")
def long_day():
    return synthetic.long_setup(seed=1)


@pytest.fixture(scope="module")
def short_day():
    return synthetic.short_setup(seed=1)


def test_long_setup_trades_like_the_video(long_day):
    bars, trades = long_day
    r = engine.run(bars, trades, NO_COSTS)
    assert len(r.levels) == 1 and r.levels[0]["side"].startswith("support")
    assert len(r.trades) == 1
    t = r.trades[0]
    assert t.side == 1
    # Entry on the bounce out of the absorbed level, stop under it, target the upper HVN.
    assert t.level_low <= t.entry <= t.level_high + 5
    assert t.stop < t.level_low
    assert t.target > 19_890
    assert t.reason == "target"
    assert t.r_multiple > 1


def test_short_setup_is_the_mirror(short_day):
    bars, trades = short_day
    r = engine.run(bars, trades, NO_COSTS)
    assert len(r.trades) == 1
    t = r.trades[0]
    assert t.side == -1 and t.stop > t.level_high and t.target < t.entry
    assert t.reason == "target" and t.pnl > 0


def test_no_lookahead(long_day):
    """Cutting the data right after the entry bar must give the same entry."""
    bars, trades = long_day
    full = engine.run(bars, trades, NO_COSTS).trades[0]
    cut = full.entry_time + pd.Timedelta(minutes=1)
    part = engine.run(bars[bars.index <= cut], trades[trades.index < cut + pd.Timedelta(minutes=1)], NO_COSTS)
    assert part.trades[0].entry_time == full.entry_time
    assert part.trades[0].entry == pytest.approx(full.entry)
    assert part.trades[0].stop == pytest.approx(full.stop)


def test_fees_reduce_pnl(long_day):
    bars, trades = long_day
    free = engine.run(bars, trades, NO_COSTS).trades[0]
    paid = engine.run(bars, trades, replace(NO_COSTS, backtest=BacktestConfig(fee_bps=25, slippage_bps=0)))
    assert paid.trades[0].pnl < free.pnl
    assert paid.trades[0].fees > 0


def test_side_filters(long_day):
    bars, trades = long_day
    cfg = replace(NO_COSTS, strategy=StrategyConfig(allow_longs=False))
    assert engine.run(bars, trades, cfg).trades == []


def test_bars_only_mode_runs(long_day):
    bars, _ = long_day
    r = engine.run(bars, None, NO_COSTS)
    assert r.delta_source.startswith("bars")
    assert r.summary()["trades"] == len(r.trades)


def test_position_sizing_respects_risk(long_day):
    bars, trades = long_day
    t = engine.run(bars, trades, NO_COSTS).trades[0]
    risked = abs(t.entry - t.stop) * t.qty
    notional = t.entry * t.qty
    assert risked <= 10_000 * 0.01 + 1e-6
    assert notional <= 10_000 * 1.0 + 1e-6


def test_multi_session_equity_curve(long_day, short_day):
    bars = pd.concat([long_day[0], short_day[0]])
    trades = pd.concat([long_day[1], short_day[1]])
    r = engine.run(bars, trades, NO_COSTS)
    assert len(r.trades) == 2
    assert r.equity.iloc[-1] == pytest.approx(10_000 + sum(t.pnl for t in r.trades))
    s = r.summary()
    assert s["win_rate_pct"] == 100.0 and s["exits"] == {"target": 2}


def test_session_keys():
    idx = pd.to_datetime(["2026-01-01 23:59", "2026-01-02 00:00", "2026-01-02 13:30"], utc=True)
    keys = engine._session_keys(pd.DatetimeIndex(idx), 0, 24)
    assert [str(k.date()) for k in keys] == ["2026-01-01", "2026-01-02", "2026-01-02"]
    keys = engine._session_keys(pd.DatetimeIndex(idx), 13, 24)
    assert [k.hour for k in keys] == [13, 13, 13]
    assert str(keys[2].date()) == "2026-01-02" and str(keys[0].date()) == "2026-01-01"
