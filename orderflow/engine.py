"""Strategy + backtest for the volume-profile / delta / TPO setup.

The setup (long side; shorts are the mirror image):

1. LEVEL     The developing session profile shows "one price" where an LVN,
             single prints and a buyer-side delta outlier line up — buyers
             drove price through there fast (Profile.levels()).
2. DEPART    Price moves away above the level.
3. RETURN    Price pulls back and trades into the level.
4. ABSORB    Sellers hit it hard (session-relative heavy negative delta
             while touching) but no bar closes through the level.
5. CONFIRM   A green bar with positive delta closes back above the level:
             buyers take control -> enter long at that bar's close.
6. MANAGE    Stop just under the level / touch low, target the next HVN
             above. Anything open at session end is closed.

Profiles are rebuilt only at the end of each TPO period from bars already
closed, so decisions never use future data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from orderflow import footprint as fpmod
from orderflow.config import Config
from orderflow.profile import Level, Profile


TRADE_COLUMNS = [
    "session", "side", "level_low", "level_high", "entry_time", "entry", "stop",
    "target", "exit_time", "exit", "reason", "qty", "pnl", "fees", "r",
]


@dataclass
class Trade:
    session: str
    side: int  # +1 long, -1 short
    level_low: float
    level_high: float
    entry_time: pd.Timestamp
    entry: float
    stop: float
    target: float
    qty: float
    exit_time: pd.Timestamp | None = None
    exit: float | None = None
    reason: str = ""
    pnl: float = 0.0
    fees: float = 0.0

    @property
    def r_multiple(self) -> float:
        risk = abs(self.entry - self.stop) * self.qty
        return self.pnl / risk if risk > 0 else 0.0


@dataclass
class _LevelState:
    level: Level
    detected_at: pd.Timestamp
    state: str = "waiting"  # waiting -> ready -> touching -> done
    touch_start: int = -1
    extreme: float = 0.0
    absorbed: bool = False


@dataclass
class Result:
    trades: list[Trade]
    equity: pd.Series
    levels: list[dict] = field(default_factory=list)
    delta_source: str = "bars"

    def trades_frame(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame(columns=TRADE_COLUMNS)
        rows = [
            {
                "session": t.session,
                "side": "long" if t.side > 0 else "short",
                "level_low": t.level_low,
                "level_high": t.level_high,
                "entry_time": t.entry_time,
                "entry": t.entry,
                "stop": t.stop,
                "target": t.target,
                "exit_time": t.exit_time,
                "exit": t.exit,
                "reason": t.reason,
                "qty": t.qty,
                "pnl": t.pnl,
                "fees": t.fees,
                "r": t.r_multiple,
            }
            for t in self.trades
        ]
        return pd.DataFrame(rows)

    def summary(self) -> dict:
        n = len(self.trades)
        start = float(self.equity.iloc[0]) if len(self.equity) else 0.0
        end = float(self.equity.iloc[-1]) if len(self.equity) else 0.0
        out = {
            "delta_source": self.delta_source,
            "levels_found": len(self.levels),
            "trades": n,
            "start_equity": round(start, 2),
            "end_equity": round(end, 2),
            "total_return_pct": round((end / start - 1) * 100, 2) if start else 0.0,
        }
        if n:
            pnl = np.array([t.pnl for t in self.trades])
            r = np.array([t.r_multiple for t in self.trades])
            gains, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
            peak = self.equity.cummax()
            out.update(
                win_rate_pct=round(float((pnl > 0).mean() * 100), 1),
                avg_r=round(float(r.mean()), 2),
                profit_factor=round(float(gains / losses), 2) if losses > 0 else float("inf"),
                max_drawdown_pct=round(float(((self.equity / peak) - 1).min() * 100), 2),
                exits={k: int(v) for k, v in pd.Series([t.reason for t in self.trades]).value_counts().items()},
            )
        return out


def _session_keys(index: pd.DatetimeIndex, start_hour: int, hours: int) -> pd.DatetimeIndex:
    shifted = index - pd.Timedelta(hours=start_hour)
    anchor = shifted.floor("D")
    block = ((shifted - anchor) // pd.Timedelta(hours=hours)).astype(int)
    return anchor + pd.to_timedelta(np.asarray(block) * hours, unit="h") + pd.Timedelta(hours=start_hour)


def run(bars: pd.DataFrame, trades: pd.DataFrame | None = None, cfg: Config | None = None) -> Result:
    """Backtest. ``bars``: 1-minute OHLCV indexed by UTC time.
    ``trades`` (optional): price/size/side with taker side for real delta."""
    cfg = cfg or Config()
    bt = cfg.backtest
    bars = bars.sort_index()
    use_trades = trades is not None and not trades.empty
    keys = _session_keys(bars.index, bt.session_start_hour_utc, bt.session_hours)

    equity = bt.initial_equity
    curve = [(bars.index[0] if len(bars) else pd.Timestamp.now(tz="UTC"), equity)]
    all_trades: list[Trade] = []
    level_log: list[dict] = []

    for session_start, sbars in bars.groupby(keys, sort=True):
        session_start = pd.Timestamp(session_start)
        session_end = session_start + pd.Timedelta(hours=bt.session_hours)
        strades = trades[(trades.index >= session_start) & (trades.index < session_end)] if use_trades else None
        new_trades, equity = _run_session(sbars, strades, session_start, cfg, equity, level_log)
        for t in new_trades:
            curve.append((t.exit_time, curve[-1][1] + t.pnl))
        all_trades.extend(new_trades)

    eq = pd.Series([v for _, v in curve], index=pd.DatetimeIndex([k for k, _ in curve]), name="equity")
    return Result(all_trades, eq, level_log, "trades" if use_trades else "bars (approximate)")


def _run_session(
    sbars: pd.DataFrame,
    strades: pd.DataFrame | None,
    session_start: pd.Timestamp,
    cfg: Config,
    equity: float,
    level_log: list[dict],
) -> tuple[list[Trade], float]:
    pc, sc, bt = cfg.profile, cfg.strategy, cfg.backtest
    n = len(sbars)
    if n < 2:
        return [], equity
    bin_size = pc.bin_size or fpmod.auto_bin_size(float(sbars["open"].iloc[0]))
    if strades is not None and not strades.empty:
        fp = fpmod.from_trades(sbars, strades, bin_size)
    else:
        fp = fpmod.from_bars(sbars, bin_size)
    fp = fp.sort_values("bar", kind="stable").reset_index(drop=True)
    fp_bar = fp["bar"].to_numpy()
    bar_d = fpmod.bar_delta(fp, n)
    abs_d_cum = np.abs(bar_d)

    o, h, l, c = (sbars[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    times = sbars.index
    period = ((times - session_start).total_seconds() // (pc.tpo_minutes * 60)).astype(int).to_numpy()
    boundary = np.append(period[1:] != period[:-1], True)

    slip = bt.slippage_bps / 1e4
    fee = bt.fee_bps / 1e4
    session_label = session_start.strftime("%Y-%m-%d %H:%M")

    profile: Profile | None = None
    states: list[_LevelState] = []
    pos: Trade | None = None
    done: list[Trade] = []

    def close_position(i: int, price: float, reason: str) -> None:
        nonlocal pos, equity
        assert pos is not None
        fill = price * (1 - slip * pos.side)
        pos.exit_time, pos.exit, pos.reason = times[i], fill, reason
        pos.fees += abs(fill * pos.qty) * fee
        pos.pnl = (fill - pos.entry) * pos.qty * pos.side - pos.fees
        equity += pos.pnl
        done.append(pos)
        pos = None

    for i in range(n):
        # ---- 1. manage the open position on this bar ---------------------
        if pos is not None and times[i] > pos.entry_time:
            if pos.side > 0:
                if o[i] <= pos.stop:
                    close_position(i, o[i], "stop")
                elif l[i] <= pos.stop:
                    close_position(i, pos.stop, "stop")
                elif h[i] >= pos.target:
                    close_position(i, max(o[i], pos.target), "target")
            else:
                if o[i] >= pos.stop:
                    close_position(i, o[i], "stop")
                elif h[i] >= pos.stop:
                    close_position(i, pos.stop, "stop")
                elif l[i] <= pos.target:
                    close_position(i, min(o[i], pos.target), "target")

        # ---- 2. walk each level's state machine --------------------------
        med_abs = float(np.median(abs_d_cum[: i + 1][abs_d_cum[: i + 1] > 0])) if np.any(abs_d_cum[: i + 1] > 0) else 0.0
        can_enter = pos is None and len(done) < sc.max_trades_per_session and i < n - 1
        for st in states:
            if st.state == "done":
                continue
            lv, side = st.level, st.level.direction
            if (side > 0 and not sc.allow_longs) or (side < 0 and not sc.allow_shorts):
                st.state = "done"
                continue
            b = lv.bin_size
            # Express everything as "long" by flipping prices for shorts.
            if side > 0:
                near_edge, far_edge = lv.high, lv.low
                bar_toward, bar_away, close_i = l[i], h[i], c[i]
            else:
                near_edge, far_edge = -lv.low, -lv.high
                bar_toward, bar_away, close_i = -h[i], -l[i], -c[i]
            broke = close_i < far_edge - sc.break_tolerance_bins * b

            if st.state == "waiting":
                if close_i > near_edge + sc.min_departure_bins * b:
                    st.state = "ready"
                continue

            if st.state == "ready":
                if bar_toward <= near_edge + sc.touch_tolerance_bins * b:
                    if broke:
                        st.state = "done"
                        continue
                    st.state, st.touch_start = "touching", i
                    st.extreme, st.absorbed = bar_toward, False
                else:
                    continue

            # touching
            if broke:
                st.state = "done"
                continue
            left_zone = not st.absorbed and close_i > near_edge + sc.min_departure_bins * b
            if left_zone or i - st.touch_start > sc.confirm_within_bars:
                st.state = "ready"  # that touch did nothing; wait for the next one
                continue
            st.extreme = min(st.extreme, bar_toward)
            d_i = bar_d[i] * side  # >0 = with the level's side
            if not st.absorbed:
                # Absorbed = at least one heavy opposite-side bar while the
                # level holds (no close through it, checked above).
                if med_abs > 0 and -d_i >= sc.absorb_mult * med_abs:
                    st.absorbed = True
                continue  # confirmation must come on a later bar
            # Buyers take control: green bar, positive delta, closes above the
            # previous bar's high, and still above the level's far edge.
            green = (c[i] - o[i]) * side > 0
            prev_away = h[i - 1] if side > 0 else -l[i - 1]
            if not (d_i > 0 and green and close_i > prev_away and close_i >= far_edge):
                continue
            if not can_enter or profile is None:
                st.state = "done"
                continue

            entry = c[i] * (1 + slip * side)
            stop = (st.extreme if side > 0 else -st.extreme)
            stop = min(stop, lv.low) - sc.stop_buffer_bins * b if side > 0 else max(stop, lv.high) + sc.stop_buffer_bins * b
            target = profile.next_hvn_above(entry) if side > 0 else profile.next_hvn_below(entry)
            risk = abs(entry - stop)
            reward = abs(target - entry) if target is not None else 0.0
            if risk <= 0 or reward / risk < sc.min_reward_risk:
                st.state = "waiting"  # no room to the next HVN; wait for a cleaner retest
                continue
            st.state = "done"
            qty = min(equity * bt.risk_per_trade / risk, equity * bt.max_leverage / entry)
            if qty <= 0:
                continue
            pos = Trade(
                session=session_label,
                side=side,
                level_low=lv.low,
                level_high=lv.high,
                entry_time=times[i],
                entry=entry,
                stop=stop,
                target=target,
                qty=qty,
                fees=entry * qty * fee,
            )
            can_enter = False

        # ---- 3. at each TPO period close, rebuild the profile ------------
        if boundary[i]:
            hi_row = int(np.searchsorted(fp_bar, i, side="right"))
            profile = Profile.build(fp.iloc[:hi_row], sbars.iloc[: i + 1], bin_size, pc, session_start)
            if not profile.empty:
                for lv in profile.levels():
                    if any(
                        s.level.direction == lv.direction
                        and s.level.low_bin <= lv.high_bin
                        and lv.low_bin <= s.level.high_bin
                        for s in states
                    ):
                        continue
                    states.append(_LevelState(lv, times[i]))
                    level_log.append(
                        {
                            "session": session_label,
                            "detected_at": times[i],
                            "side": "support (long)" if lv.direction > 0 else "resistance (short)",
                            "low": lv.low,
                            "high": lv.high,
                            "delta": lv.delta,
                        }
                    )

    if pos is not None:
        close_position(n - 1, c[n - 1], "session_end")
    return done, equity
