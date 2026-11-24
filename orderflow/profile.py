"""Session profile: the three views from the video, per price bin.

* WHERE  — volume profile: POC, value area, high/low volume nodes (HVN/LVN)
* WHO    — delta: buyer minus seller volume, and one-sided "outlier" bins
* TIME   — TPO: how many 30-minute periods traded at each price, and
           "single prints" (prices only one period ever visited)

``Profile.levels()`` returns the "ONE PRICE" zones: an LVN that lines up
with single prints and a delta outlier. Those are the levels the strategy
waits for price to come back to.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from orderflow.config import ProfileConfig
from orderflow.footprint import price_to_bin


@dataclass(frozen=True)
class Level:
    low_bin: int
    high_bin: int
    bin_size: float
    # +1: buyers drove price through it (support for longs);
    # -1: sellers drove price through it (resistance for shorts).
    direction: int
    delta: float

    @property
    def low(self) -> float:
        return self.low_bin * self.bin_size

    @property
    def high(self) -> float:
        return (self.high_bin + 1) * self.bin_size

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2


class Profile:
    """Profile of one (partial) session. ``table`` is indexed by bin with
    columns volume, buy, sell, delta, tpo over a contiguous bin range."""

    def __init__(self, table: pd.DataFrame, bin_size: float, cfg: ProfileConfig):
        self.table = table
        self.bin_size = bin_size
        self.cfg = cfg

    # ------------------------------------------------------------------ build
    @classmethod
    def build(
        cls,
        footprint: pd.DataFrame,
        bars: pd.DataFrame,
        bin_size: float,
        cfg: ProfileConfig,
        session_start: pd.Timestamp,
    ) -> "Profile":
        """``footprint`` rows and ``bars`` must cover the same bars."""
        if bars.empty:
            return cls(pd.DataFrame(columns=["volume", "buy", "sell", "delta", "tpo"]), bin_size, cfg)

        # TPO: each period touches every bin between its low and high.
        period = ((bars.index - session_start).total_seconds() // (cfg.tpo_minutes * 60)).astype(int)
        per = pd.DataFrame(
            {
                "lo": price_to_bin(bars["low"].to_numpy(), bin_size),
                "hi": price_to_bin(bars["high"].to_numpy(), bin_size),
                "p": np.asarray(period),
            }
        ).groupby("p").agg(lo=("lo", "min"), hi=("hi", "max"))

        lo_bin = int(min(per["lo"].min(), footprint["bin"].min() if len(footprint) else per["lo"].min()))
        hi_bin = int(max(per["hi"].max(), footprint["bin"].max() if len(footprint) else per["hi"].max()))
        bins = np.arange(lo_bin, hi_bin + 1)

        tpo_diff = np.zeros(len(bins) + 1)
        np.add.at(tpo_diff, per["lo"].to_numpy() - lo_bin, 1)
        np.add.at(tpo_diff, per["hi"].to_numpy() - lo_bin + 1, -1)
        tpo = np.cumsum(tpo_diff)[:-1]

        agg = footprint.groupby("bin")[["volume", "buy", "sell"]].sum().reindex(bins, fill_value=0.0)
        table = agg.astype(float)
        table["delta"] = table["buy"] - table["sell"]
        table["tpo"] = tpo.astype(int)
        table.index.name = "bin"
        return cls(table, bin_size, cfg)

    # ----------------------------------------------------------------- basics
    @property
    def empty(self) -> bool:
        return self.table.empty or float(self.table["volume"].sum()) <= 0

    def price(self, b: int) -> float:
        """Centre price of a bin."""
        return (b + 0.5) * self.bin_size

    @property
    def poc_bin(self) -> int:
        return int(self.table["volume"].idxmax())

    def value_area(self) -> tuple[int, int]:
        """(VAL bin, VAH bin): grow out from the POC, always adding the
        heavier neighbour, until ``value_area`` of volume is covered."""
        vol = self.table["volume"].to_numpy()
        bins = self.table.index.to_numpy()
        i = j = int(np.argmax(vol))
        total, target = vol[i], vol.sum() * self.cfg.value_area
        while total < target and (i > 0 or j < len(vol) - 1):
            below = vol[i - 1] if i > 0 else -1.0
            above = vol[j + 1] if j < len(vol) - 1 else -1.0
            if above >= below:
                j += 1
                total += above
            else:
                i -= 1
                total += below
        return int(bins[i]), int(bins[j])

    def _smoothed(self) -> np.ndarray:
        return (
            self.table["volume"]
            .rolling(self.cfg.smooth_bins, center=True, min_periods=1)
            .mean()
            .to_numpy()
        )

    # ------------------------------------------------------------- WHERE
    def hvn_bins(self) -> list[int]:
        """Centres of local volume peaks (fat bars = business)."""
        s = self._smoothed()
        if len(s) == 0:
            return []
        padded = np.concatenate([[-1.0], s, [-1.0]])
        is_peak = (padded[1:-1] >= padded[:-2]) & (padded[1:-1] >= padded[2:])
        is_peak &= s >= self.cfg.hvn_ratio * s.max()
        bins = self.table.index.to_numpy()
        # Collapse plateaus into their centre bin.
        out, run = [], []
        for k in range(len(s)):
            if is_peak[k] and (not run or k == run[-1] + 1):
                run.append(k)
            else:
                if run:
                    out.append(int(bins[run[len(run) // 2]]))
                run = [k] if is_peak[k] else []
        if run:
            out.append(int(bins[run[len(run) // 2]]))
        return out

    def lvn_bins(self) -> list[int]:
        """Valleys: much thinner than the volume found both above and below."""
        s = self._smoothed()
        if len(s) < 3:
            return []
        max_below = np.concatenate([[0.0], np.maximum.accumulate(s)[:-1]])
        max_above = np.concatenate([np.maximum.accumulate(s[::-1])[::-1][1:], [0.0]])
        walls = np.minimum(max_below, max_above)
        mask = (walls > 0) & (s <= self.cfg.lvn_valley_ratio * walls)
        return [int(b) for b in self.table.index.to_numpy()[mask]]

    # --------------------------------------------------------------- WHO
    def delta_outlier_bins(self) -> list[int]:
        t = self.table[self.table["volume"] > 0]
        if t.empty:
            return []
        abs_d = t["delta"].abs()
        med = float(abs_d.median())
        mask = (abs_d >= self.cfg.delta_outlier_mult * max(med, 1e-12)) & (
            abs_d / t["volume"] >= self.cfg.delta_outlier_imbalance
        )
        return [int(b) for b in t.index[mask]]

    # -------------------------------------------------------------- TIME
    def single_print_bins(self) -> list[int]:
        """Bins visited by a single TPO period, with accepted (2+ period)
        prices both above and below — i.e. inside the profile, not a tail."""
        tpo = self.table["tpo"].to_numpy()
        if len(tpo) < 3:
            return []
        accepted = tpo >= 2
        below = np.concatenate([[False], np.logical_or.accumulate(accepted)[:-1]])
        above = np.concatenate([np.logical_or.accumulate(accepted[::-1])[::-1][1:], [False]])
        mask = (tpo == 1) & below & above
        return [int(b) for b in self.table.index.to_numpy()[mask]]

    # --------------------------------------------------------- ONE PRICE
    def levels(self) -> list[Level]:
        tol = self.cfg.confluence_tolerance_bins
        lvn = set(self.lvn_bins())
        singles = np.array(sorted(self.single_print_bins()))
        outliers = np.array(sorted(self.delta_outlier_bins()))
        if not lvn or singles.size == 0 or outliers.size == 0:
            return []

        def near(arr: np.ndarray, b: int) -> bool:
            return bool(np.any(np.abs(arr - b) <= tol))

        hits = sorted(b for b in lvn if near(singles, b) and near(outliers, b))
        levels: list[Level] = []
        run: list[int] = []
        for b in hits + [None]:  # sentinel flushes the last run
            if b is not None and (not run or b - run[-1] <= tol + 1):
                run.append(b)
                continue
            if run:
                lo, hi = run[0], run[-1]
                zone = outliers[(outliers >= lo - tol) & (outliers <= hi + tol)]
                d = float(self.table.loc[zone, "delta"].sum())
                if d != 0:
                    levels.append(Level(lo, hi, self.bin_size, 1 if d > 0 else -1, d))
            run = [b] if b is not None else []
        return levels

    def next_hvn_above(self, price: float) -> float | None:
        cands = [self.price(b) for b in self.hvn_bins() if self.price(b) > price]
        return min(cands) if cands else None

    def next_hvn_below(self, price: float) -> float | None:
        cands = [self.price(b) for b in self.hvn_bins() if self.price(b) < price]
        return max(cands) if cands else None
