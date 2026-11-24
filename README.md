# Order Flow Strategy: Volume Profile + Delta + TPO

This branch replaces the previous multi-strategy platform with a single
strategy: the "where / who / how long" setup. The full previous app is still
on `main`.

| View | Question | What it shows |
|---|---|---|
| **Volume profile** | Where? | Fat bars (HVN, POC) = business done. Thin bars (LVN) = price moved through fast. |
| **Delta** | Who? | Buyers lifting the offer vs. sellers hitting the bid, per price. |
| **TPO** | How long? | 30-minute periods at each price. Wide = accepted; *single prints* = barely visited. |

## The setup (long; shorts are the mirror)

1. **Level**: in the developing session profile, find *one price* where an
   **LVN**, **single prints** and a **buyer-side delta outlier** line up.
   Buyers drove price through it fast.
2. **Depart**: price closes away above the level.
3. **Return**: price pulls back into the level.
4. **Absorb**: while it touches, at least one bar shows heavy selling
   (delta at least `absorb_mult` × the session's median bar delta), yet no
   bar closes through the level.
5. **Confirm**: a green bar with positive delta closes above the previous
   bar's high. Buyers have taken control, so enter long at that close.
6. **Manage**: stop just beyond the level / touch low. Target the **next
   HVN** above. The trade is skipped if reward:risk is below
   `min_reward_risk`. Anything still open is closed at session end.

Profiles are rebuilt only at the close of each 30-minute TPO period, from
completed bars, so the backtest never uses future data
(`tests/test_engine.py::test_no_lookahead`).

Every number in the rules is a setting in `orderflow/config.py`.

## Data

Crypto via Alpaca (no API key required for crypto data; keys from `.env`
are used if set):

* **1-minute bars**: volume profile and TPO.
* **Trades** (`--trades`): Alpaca crypto trades carry the taker side, so
  **delta is real**. Without trades, delta is approximated from where each
  candle closed in its range. That is fine for profile/TPO, but absorption
  detection becomes a rough guess.

## Usage

```bash
pip install -r requirements.txt

# 1. See it work on a synthetic re-enactment of the video
python -m orderflow demo

# 2. Download real data (cached under ./data, one file per day)
python -m orderflow download --symbol BTC/USD --start 2026-10-01 --end 2026-10-31 --trades

# 3. Backtest
python -m orderflow backtest --symbol BTC/USD --start 2026-10-01 --end 2026-10-31 --out results/

# 4. Inspect one day's profile and its levels
python -m orderflow levels --symbol BTC/USD --date 2026-10-15
```

Useful flags: `--bin-size` (price bucket; default ≈ 0.05% of price),
`--fee-bps`, `--slippage-bps`, `--risk`, `--long-only`, `--short-only`,
`--no-trades`.

## Costs matter

The video's example targets roughly 0.1% moves on a futures contract.
Alpaca's crypto **taker fee is 0.25% per side** at the lowest tier (the
default `fee_bps=25`). A round trip costs about 0.5%, which is several times
the profit of a typical setup on 1-minute data. Run backtests with your
real fee tier. Expect small, fast setups to be unprofitable at retail
crypto fees unless the bin size, and therefore the move to the next HVN, is
much larger.

## Layout

```
orderflow/
  config.py      all strategy / backtest parameters
  footprint.py   per-bar, per-price buy/sell volume (from trades or candles)
  profile.py     POC, value area, HVN/LVN, single prints, delta outliers, levels
  engine.py      strategy state machine + backtest + metrics
  synthetic.py   synthetic sessions that re-enact the video (tests/demo)
  data/          Alpaca client + local day-file cache
  cli.py         demo / download / backtest / levels
tests/
```

```bash
pytest -q
```

## Not included (yet)

* Live/paper trading. This branch is research and backtest only.
* Futures (the video's market). Alpaca does not offer them.
* Stocks. Tiingo IEX bars are about 2–3% of US volume, which distorts the
  profile. Real stock delta needs paid trade + quote data.
