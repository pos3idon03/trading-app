from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dal import instrument_dal
from features.backtesting.bar_loader import load_backtest_bars


def _bar_date(bar: dict) -> date:
    t = bar["time"]
    if isinstance(t, datetime):
        dt = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        return dt.date()
    if isinstance(t, date):
        return t
    parsed = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    return parsed.date()


@dataclass
class ReturnsPanel:
    symbols: list[str]
    dates: list[date]
    bars_by_symbol: dict[str, list[dict]]
    log_returns: dict[str, list[float | None]]
    warnings: list[str] = field(default_factory=list)


def _log_returns_for_bars(bars: list[dict]) -> list[float | None]:
    if not bars:
        return []
    closes = [float(b["close"]) for b in bars]
    returns: list[float | None] = [None]
    for i in range(1, len(closes)):
        prev, curr = closes[i - 1], closes[i]
        if prev <= 0 or curr <= 0:
            returns.append(None)
        else:
            returns.append(__import__("math").log(curr / prev))
    return returns


def align_bars_by_date(
    bars_by_symbol: dict[str, list[dict]],
) -> tuple[list[date], dict[str, list[dict]]]:
    if not bars_by_symbol:
        return [], {}

    date_sets = []
    for bars in bars_by_symbol.values():
        date_sets.append({_bar_date(b) for b in bars})

    common_dates = sorted(set.intersection(*date_sets)) if date_sets else []
    aligned: dict[str, list[dict]] = {}
    for symbol, bars in bars_by_symbol.items():
        by_date = {_bar_date(b): b for b in bars}
        aligned[symbol] = [by_date[d] for d in common_dates if d in by_date]
    return common_dates, aligned


async def load_returns_panel(
    session: AsyncSession,
    *,
    symbols: list[str],
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
) -> ReturnsPanel:
    warnings: list[str] = []
    bars_by_symbol: dict[str, list[dict]] = {}

    for symbol in symbols:
        instrument = await instrument_dal.get_by_symbol(session, symbol)
        if not instrument:
            warnings.append(f"Instrument not found: {symbol}")
            continue
        bars = await load_backtest_bars(
            session,
            instrument_id=instrument["id"],
            timeframe=timeframe,
            start=start,
            end=end,
        )
        if not bars:
            warnings.append(f"No bars for {symbol}")
            continue
        bars_by_symbol[symbol.upper()] = bars

    if not bars_by_symbol:
        raise ValueError("No bar data loaded for any symbol in panel")

    dates, aligned = align_bars_by_date(bars_by_symbol)
    if not dates:
        raise ValueError("No common trading dates across symbols")

    log_returns = {
        sym: _log_returns_for_bars(aligned[sym]) for sym in aligned
    }
    return ReturnsPanel(
        symbols=sorted(aligned.keys()),
        dates=dates,
        bars_by_symbol=aligned,
        log_returns=log_returns,
        warnings=warnings,
    )


def build_return_matrix(
    panel: ReturnsPanel,
    end_index: int,
    lookback: int,
) -> list[list[float]]:
    """Rows are time steps, cols are symbols — for HRP/PCA."""
    start_index = max(1, end_index - lookback + 1)
    matrix: list[list[float]] = []
    for i in range(start_index, end_index + 1):
        row: list[float] = []
        complete = True
        for sym in panel.symbols:
            ret = panel.log_returns[sym][i]
            if ret is None:
                complete = False
                break
            row.append(ret)
        if complete:
            matrix.append(row)
    return matrix
