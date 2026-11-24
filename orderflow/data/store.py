"""Local cache: one gzipped CSV per symbol/kind/UTC day under ./data/."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from orderflow.data import alpaca

DEFAULT_DIR = Path("data")


def _path(root: Path, symbol: str, kind: str, day: date) -> Path:
    safe = alpaca.normalize_symbol(symbol).replace("/", "")
    return root / safe / kind / f"{day.isoformat()}.csv.gz"


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def download(symbol: str, start: date, end: date, *, trades: bool, root: Path = DEFAULT_DIR, force: bool = False) -> None:
    """Download bars (and optionally trades) day by day; skips cached days."""
    kinds = ["bars", "trades"] if trades else ["bars"]
    today = datetime.now(timezone.utc).date()
    for day in _days(start, end):
        t0 = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        t1 = t0 + timedelta(days=1)
        for kind in kinds:
            path = _path(root, symbol, kind, day)
            if path.exists() and not force:
                continue
            df = alpaca.fetch_bars(symbol, t0, t1) if kind == "bars" else alpaca.fetch_trades(symbol, t0, t1)
            df = df[df.index < t1]
            path.parent.mkdir(parents=True, exist_ok=True)
            if day < today:  # don't cache a partial day
                df.to_csv(path)
            print(f"{kind:6s} {day}  {len(df):>8,d} rows")


def load(symbol: str, start: date, end: date, kind: str, root: Path = DEFAULT_DIR) -> pd.DataFrame:
    frames = []
    for day in _days(start, end):
        path = _path(root, symbol, kind, day)
        if path.exists():
            frames.append(pd.read_csv(path, index_col="time", parse_dates=["time"]))
    if not frames:
        return alpaca._empty_bars() if kind == "bars" else alpaca._empty_trades()
    df = pd.concat(frames).sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    if kind == "trades":
        df["side"] = df["side"].fillna("").astype(str)
    return df
