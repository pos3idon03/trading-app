"""Footprint: traded volume split into buyer/seller volume per bar per price bin.

Two sources:

* ``from_trades`` — exact. Each trade's taker side says whether a buyer
  lifted the offer or a seller hit the bid. This is real delta.
* ``from_bars`` — approximation when only candles exist. A bar's volume is
  spread evenly over the bins it traded through, and its buy share is
  estimated from where it closed inside its range. Good enough for volume
  profile and TPO; delta from this is a rough guess.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

COLUMNS = ["bar", "bin", "volume", "buy", "sell"]


def price_to_bin(price: np.ndarray | float, bin_size: float) -> np.ndarray:
    # Small epsilon so that prices sitting exactly on a bin edge are stable.
    return np.floor(np.asarray(price, dtype=float) / bin_size + 1e-9).astype(np.int64)


def auto_bin_size(reference_price: float) -> float:
    """~0.05% of price, rounded to 1/2/5 x 10^k (BTC at 90k -> 50)."""
    raw = reference_price * 0.0005
    exp = math.floor(math.log10(raw))
    base = raw / 10**exp
    nice = 1 if base < 1.5 else 2 if base < 3.5 else 5 if base < 7.5 else 10
    return float(nice * 10**exp)


def from_trades(bars: pd.DataFrame, trades: pd.DataFrame, bin_size: float) -> pd.DataFrame:
    if trades.empty or bars.empty:
        return pd.DataFrame(columns=COLUMNS)
    minute = trades.index.floor("min")
    pos = bars.index.get_indexer(minute)
    mask = pos >= 0
    t = trades[mask]
    size = t["size"].to_numpy(float)
    is_buy = (t["side"].to_numpy() == "B").astype(float)
    is_sell = (t["side"].to_numpy() == "S").astype(float)
    df = pd.DataFrame(
        {
            "bar": pos[mask],
            "bin": price_to_bin(t["price"].to_numpy(), bin_size),
            "volume": size,
            "buy": size * is_buy,
            "sell": size * is_sell,
        }
    )
    return df.groupby(["bar", "bin"], as_index=False).sum()[COLUMNS]


def from_bars(bars: pd.DataFrame, bin_size: float) -> pd.DataFrame:
    if bars.empty:
        return pd.DataFrame(columns=COLUMNS)
    lo = price_to_bin(bars["low"].to_numpy(), bin_size)
    hi = price_to_bin(bars["high"].to_numpy(), bin_size)
    n = hi - lo + 1
    vol = bars["volume"].to_numpy(float)
    rng = bars["high"].to_numpy(float) - bars["low"].to_numpy(float)
    # Close at the high -> all buying, at the low -> all selling, doji -> 50/50.
    close_loc = np.where(
        rng > 0,
        (bars["close"].to_numpy(float) - bars["low"].to_numpy(float)) / np.where(rng > 0, rng, 1),
        0.5,
    )
    bar_idx = np.repeat(np.arange(len(bars)), n)
    offsets = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)
    per_bin = np.repeat(vol / n, n)
    buy_share = np.repeat(close_loc, n)
    return pd.DataFrame(
        {
            "bar": bar_idx,
            "bin": np.repeat(lo, n) + offsets,
            "volume": per_bin,
            "buy": per_bin * buy_share,
            "sell": per_bin * (1 - buy_share),
        }
    )


def bar_delta(footprint: pd.DataFrame, n_bars: int) -> np.ndarray:
    """Buy minus sell volume for each bar."""
    out = np.zeros(n_bars)
    if footprint.empty:
        return out
    d = (footprint["buy"] - footprint["sell"]).to_numpy(float)
    np.add.at(out, footprint["bar"].to_numpy(np.int64), d)
    return out
