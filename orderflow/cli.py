"""Command line.

    python -m orderflow demo
    python -m orderflow download --symbol BTC/USD --start 2026-10-01 --end 2026-10-31 --trades
    python -m orderflow backtest --symbol BTC/USD --start 2026-10-01 --end 2026-10-31
    python -m orderflow levels   --symbol BTC/USD --date 2026-10-15
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd

from orderflow import engine, footprint, synthetic
from orderflow.config import Config
from orderflow.data import store
from orderflow.profile import Profile


def _config(args: argparse.Namespace) -> Config:
    cfg = Config()
    prof, strat, bt = cfg.profile, cfg.strategy, cfg.backtest
    if getattr(args, "bin_size", None):
        prof = replace(prof, bin_size=args.bin_size)
    if getattr(args, "fee_bps", None) is not None:
        bt = replace(bt, fee_bps=args.fee_bps)
    if getattr(args, "slippage_bps", None) is not None:
        bt = replace(bt, slippage_bps=args.slippage_bps)
    if getattr(args, "risk", None) is not None:
        bt = replace(bt, risk_per_trade=args.risk)
    if getattr(args, "long_only", False):
        strat = replace(strat, allow_shorts=False)
    if getattr(args, "short_only", False):
        strat = replace(strat, allow_longs=False)
    return Config(profile=prof, strategy=strat, backtest=bt)


def _report(result: engine.Result, out: Path | None) -> None:
    print(json.dumps(result.summary(), indent=2, default=str))
    tf = result.trades_frame()
    if not tf.empty:
        cols = ["side", "entry_time", "entry", "stop", "target", "exit", "reason", "r"]
        print(tf[cols].to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
    if out:
        out.mkdir(parents=True, exist_ok=True)
        tf.to_csv(out / "trades.csv", index=False)
        pd.DataFrame(result.levels).to_csv(out / "levels.csv", index=False)
        result.equity.to_csv(out / "equity.csv")
        (out / "summary.json").write_text(json.dumps(result.summary(), indent=2, default=str))
        print(f"\nWrote {out}/trades.csv, levels.csv, equity.csv, summary.json")


def cmd_demo(args: argparse.Namespace) -> None:
    from orderflow.config import BacktestConfig, ProfileConfig

    cfg = Config(
        profile=ProfileConfig(bin_size=5),
        backtest=BacktestConfig(fee_bps=args.fee_bps or 0.0, slippage_bps=0.0),
    )
    lb, lt = synthetic.long_setup(seed=args.seed)
    sb, st = synthetic.short_setup(seed=args.seed)
    bars, trades = pd.concat([lb, sb]), pd.concat([lt, st])
    print("Synthetic re-enactment of the video setup (one long day, one mirrored short day)\n")
    _report(engine.run(bars, None if args.no_trades else trades, cfg), args.out)


def cmd_download(args: argparse.Namespace) -> None:
    store.download(args.symbol, args.start, args.end, trades=args.trades, root=args.data_dir, force=args.force)


def cmd_backtest(args: argparse.Namespace) -> None:
    bars = store.load(args.symbol, args.start, args.end, "bars", args.data_dir)
    if bars.empty:
        raise SystemExit("No bars cached for that range. Run `download` first.")
    trades = None
    if not args.no_trades:
        trades = store.load(args.symbol, args.start, args.end, "trades", args.data_dir)
        if trades.empty:
            print("No trades cached -> delta is approximated from candles (download with --trades for real delta).\n")
            trades = None
    _report(engine.run(bars, trades, _config(args)), args.out)


def cmd_levels(args: argparse.Namespace) -> None:
    cfg = _config(args)
    bars = store.load(args.symbol, args.date, args.date, "bars", args.data_dir)
    if bars.empty:
        raise SystemExit("No bars cached for that day. Run `download` first.")
    trades = store.load(args.symbol, args.date, args.date, "trades", args.data_dir)
    bin_size = cfg.profile.bin_size or footprint.auto_bin_size(float(bars["open"].iloc[0]))
    fp = footprint.from_trades(bars, trades, bin_size) if not trades.empty else footprint.from_bars(bars, bin_size)
    start = pd.Timestamp(args.date.isoformat(), tz="UTC")
    p = Profile.build(fp, bars, bin_size, cfg.profile, start)
    val, vah = p.value_area()
    hvn, lvn = set(p.hvn_bins()), set(p.lvn_bins())
    sp, out = set(p.single_print_bins()), set(p.delta_outlier_bins())
    level_bins = {b for lv in p.levels() for b in range(lv.low_bin, lv.high_bin + 1)}
    print(f"bin={bin_size}  POC={p.price(p.poc_bin):,.2f}  VAL={p.price(val):,.2f}  VAH={p.price(vah):,.2f}")
    print(f"delta source: {'trades' if not trades.empty else 'candles (approximate)'}\n")
    vmax = p.table["volume"].max()
    for b, row in p.table.iloc[::-1].iterrows():
        tags = [n for n, s in (("POC", {p.poc_bin}), ("HVN", hvn), ("LVN", lvn), ("SINGLE", sp), ("DELTA!", out), ("<< LEVEL", level_bins)) if b in s]
        bar = "#" * int(30 * row["volume"] / vmax) if vmax > 0 else ""
        print(f"{p.price(b):>12,.2f} {bar:<30} vol={row['volume']:>10,.2f} delta={row['delta']:>+10,.2f} tpo={int(row['tpo']):>2}  {' '.join(tags)}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="orderflow", description="Volume profile + delta + TPO strategy")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p: argparse.ArgumentParser, single_day: bool = False) -> None:
        p.add_argument("--symbol", default="BTC/USD")
        if single_day:
            p.add_argument("--date", type=date.fromisoformat, required=True)
        else:
            p.add_argument("--start", type=date.fromisoformat, required=True)
            p.add_argument("--end", type=date.fromisoformat, required=True)
        p.add_argument("--data-dir", type=Path, default=store.DEFAULT_DIR)

    def tuning(p: argparse.ArgumentParser) -> None:
        p.add_argument("--bin-size", type=float, help="price bucket size (default: auto)")
        p.add_argument("--fee-bps", type=float, help="fee per side in basis points")
        p.add_argument("--slippage-bps", type=float)
        p.add_argument("--risk", type=float, help="fraction of equity risked per trade")
        p.add_argument("--long-only", action="store_true")
        p.add_argument("--short-only", action="store_true")
        p.add_argument("--out", type=Path, help="directory for CSV/JSON results")

    p = sub.add_parser("demo", help="run on synthetic data that re-enacts the video")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--fee-bps", type=float, default=0.0)
    p.add_argument("--no-trades", action="store_true", help="approximate delta from candles")
    p.add_argument("--out", type=Path)
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("download", help="download Alpaca crypto bars (+ trades) to ./data")
    common(p)
    p.add_argument("--trades", action="store_true", help="also download trades (real delta)")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("backtest", help="backtest on downloaded data")
    common(p)
    tuning(p)
    p.add_argument("--no-trades", action="store_true", help="ignore trades; approximate delta from candles")
    p.set_defaults(func=cmd_backtest)

    p = sub.add_parser("levels", help="print one day's profile and the levels it produces")
    common(p, single_day=True)
    tuning(p)
    p.set_defaults(func=cmd_levels)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
