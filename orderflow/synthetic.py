"""Synthetic session that re-enacts the setup from the video.

Used by the tests and by ``python -m orderflow demo``. Prices are around
19,850-19,900 with a 5-point bin, like the example in the video.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# (minutes, start price, end price, trades per minute, buyer probability, noise)
_PHASES_LONG = [
    (240, 19855, 19855, 30, 0.50, 6.0),   # balance -> POC / lower HVN
    (3, 19862, 19893, 400, 0.95, 1.5),    # fast buyer impulse -> LVN + single prints + delta outlier
    (177, 19900, 19900, 30, 0.50, 3.5),   # balance higher -> upper HVN
    (10, 19898, 19876, 40, 0.30, 1.5),    # pullback into the level
    (6, 19874, 19874, 120, 0.15, 2.0),    # sellers hit it hard, price holds = absorbed
    (14, 19876, 19906, 60, 0.85, 1.5),    # buyers take control -> next HVN
    (150, 19903, 19903, 30, 0.50, 4.0),   # rest of the session
]


def _generate(phases, seed: int, start: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    t0 = pd.Timestamp(start, tz="UTC")
    rows = []
    minute = 0
    for minutes, p0, p1, tpm, buy_p, noise in phases:
        path = np.linspace(p0, p1, minutes + 1)
        for m in range(minutes):
            k = rng.poisson(tpm) + 1
            frac = np.sort(rng.random(k))
            base = path[m] + (path[m + 1] - path[m]) * frac
            if p0 == p1:  # balance: mean-reverting wander
                base = base + rng.normal(0, noise, size=1)
            price = np.round(base + rng.normal(0, noise / 3, size=k), 2)
            side = np.where(rng.random(k) < buy_p, "B", "S")
            size = np.round(rng.exponential(0.05, size=k) + 0.001, 4)
            ts = t0 + pd.to_timedelta(minute * 60 + frac * 59.999, unit="s")
            rows.append(pd.DataFrame({"time": ts, "price": price, "size": size, "side": side}))
            minute += 1
    trades = pd.concat(rows).set_index("time").sort_index()
    g = trades.groupby(trades.index.floor("min"))
    bars = pd.DataFrame(
        {
            "open": g["price"].first(),
            "high": g["price"].max(),
            "low": g["price"].min(),
            "close": g["price"].last(),
            "volume": g["size"].sum(),
        }
    )
    bars.index.name = "time"
    trades.index.name = "time"
    return bars, trades


def long_setup(seed: int = 7, start: str = "2026-01-05") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bars and trades for one session containing the long setup."""
    return _generate(_PHASES_LONG, seed, start)


def short_setup(seed: int = 7, start: str = "2026-01-06") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mirror image: seller impulse down, pullback up, buyers absorbed."""
    pivot = 19880.0
    phases = [
        (n, 2 * pivot - a, 2 * pivot - b, tpm, 1 - bp, noise)
        for n, a, b, tpm, bp, noise in _PHASES_LONG
    ]
    return _generate(phases, seed, start)
