"""Alpaca crypto market data: 1-minute bars and individual trades.

Crypto trades from Alpaca carry the taker side (``tks``: "B" = buyer lifted
the offer, "S" = seller hit the bid). That is what makes *real* delta
possible, instead of guessing it from candles.

Alpaca crypto data does not require an API key; if ALPACA_API_KEY and
ALPACA_SECRET_KEY are set they are sent anyway (higher rate limits).
Only the standard library is used for HTTP.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Iterator

import pandas as pd

_DEFAULT_BASE = "https://data.alpaca.markets"
_BARS_PATH = "/v1beta3/crypto/us/bars"
_TRADES_PATH = "/v1beta3/crypto/us/trades"


def normalize_symbol(symbol: str) -> str:
    """'btcusd', 'BTC-USD', 'BTC/USD' -> 'BTC/USD'."""
    s = symbol.upper().replace("-", "/").replace("_", "/")
    if "/" in s:
        return s
    for quote in ("USDT", "USDC", "USD", "BTC"):
        if s.endswith(quote) and len(s) > len(quote):
            return f"{s[: -len(quote)]}/{quote}"
    raise ValueError(f"Cannot parse crypto symbol: {symbol!r}")


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/json", "User-Agent": "orderflow-backtester"}
    key, secret = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
    if key and secret:
        headers["APCA-API-KEY-ID"] = key
        headers["APCA-API-SECRET-KEY"] = secret
    return headers


def _get(url: str, params: dict[str, str], retries: int = 4) -> dict:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    delay = 1.0
    for attempt in range(retries + 1):
        req = urllib.request.Request(full, headers=_headers())
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except urllib.error.URLError:
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("unreachable")


def _paginate(path: str, key: str, symbol: str, params: dict[str, str]) -> Iterator[dict]:
    base = os.getenv("ALPACA_DATA_BASE_URL", _DEFAULT_BASE).rstrip("/")
    page_token: str | None = None
    while True:
        p = dict(params, symbols=symbol, limit="10000")
        if page_token:
            p["page_token"] = page_token
        payload = _get(f"{base}{path}", p)
        yield from (payload.get(key) or {}).get(symbol) or []
        page_token = payload.get("next_page_token")
        if not page_token:
            return


def fetch_bars(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    """1-minute OHLCV bars, indexed by UTC time."""
    sym = normalize_symbol(symbol)
    rows = list(
        _paginate(_BARS_PATH, "bars", sym, {"timeframe": "1Min", "start": _iso(start), "end": _iso(end)})
    )
    if not rows:
        return _empty_bars()
    df = pd.DataFrame(rows).rename(
        columns={"t": "time", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
    )
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.set_index("time")[["open", "high", "low", "close", "volume"]].astype(float).sort_index()


def fetch_trades(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Individual trades with taker side: columns price, size, side ('B'/'S')."""
    sym = normalize_symbol(symbol)
    rows = list(_paginate(_TRADES_PATH, "trades", sym, {"start": _iso(start), "end": _iso(end)}))
    if not rows:
        return _empty_trades()
    df = pd.DataFrame(rows).rename(columns={"t": "time", "p": "price", "s": "size", "tks": "side"})
    df["time"] = pd.to_datetime(df["time"], utc=True, format="ISO8601")
    df = df.set_index("time")[["price", "size", "side"]].sort_index()
    df["price"] = df["price"].astype(float)
    df["size"] = df["size"].astype(float)
    df["side"] = df["side"].fillna("").astype(str).str.upper().str[:1]
    return df


def _empty_bars() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["open", "high", "low", "close", "volume"],
        index=pd.DatetimeIndex([], tz="UTC", name="time"),
        dtype=float,
    )


def _empty_trades() -> pd.DataFrame:
    df = pd.DataFrame({"price": [], "size": [], "side": []}, index=pd.DatetimeIndex([], tz="UTC", name="time"))
    return df.astype({"price": float, "size": float, "side": str})
