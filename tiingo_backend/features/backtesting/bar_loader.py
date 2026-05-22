from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dal import ohlcv_dal
from features.backtesting.signal_warmup import compute_warmup_start
from features.market_data.ohlcv_resample import SUPPORTED_TIMEFRAMES


def _to_utc_datetime(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)


def validate_timeframe(timeframe: str, label: str = "timeframe") -> None:
    if timeframe not in SUPPORTED_TIMEFRAMES:
        supported = ", ".join(sorted(SUPPORTED_TIMEFRAMES))
        raise ValueError(f"Unsupported {label}: {timeframe}. Supported: {supported}")


def collect_required_timeframes(
    strategy: str,
    params: dict,
    decision_timeframe: str,
    signal_timeframe: str | None = None,
) -> set[str]:
    validate_timeframe(decision_timeframe, "decision timeframe")
    timeframes = {decision_timeframe}

    if strategy == "strategy_ensemble":
        for leg in params.get("legs", []):
            leg_tf = leg.get("signal_timeframe") or decision_timeframe
            validate_timeframe(leg_tf, "leg signal timeframe")
            timeframes.add(leg_tf)
    else:
        effective = signal_timeframe or decision_timeframe
        validate_timeframe(effective, "signal timeframe")
        timeframes.add(effective)

    return timeframes


def normalize_signal_timeframes(
    strategy: str,
    params: dict,
    decision_timeframe: str,
    signal_timeframe: str | None,
) -> tuple[dict, str]:
    if strategy == "strategy_ensemble":
        normalized = dict(params)
        legs = []
        for leg in params.get("legs", []):
            leg_copy = dict(leg)
            leg_copy["signal_timeframe"] = leg.get("signal_timeframe") or decision_timeframe
            legs.append(leg_copy)
        normalized["legs"] = legs
        return normalized, decision_timeframe

    effective = signal_timeframe or decision_timeframe
    return params, effective


async def load_backtest_bars(
    session: AsyncSession,
    instrument_id: int,
    timeframe: str,
    start: date | datetime | None,
    end: date | datetime | None,
) -> list[dict]:
    bars_by_tf = await load_multi_timeframe_bars(
        session,
        instrument_id,
        {timeframe},
        start,
        end,
    )
    return bars_by_tf[timeframe]


async def load_multi_timeframe_bars(
    session: AsyncSession,
    instrument_id: int,
    timeframes: set[str],
    start: date | datetime | None,
    end: date | datetime | None,
    *,
    decision_timeframe: str | None = None,
    warmup_bars_by_tf: dict[str, int] | None = None,
) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    warmup = warmup_bars_by_tf or {}

    for timeframe in sorted(timeframes):
        validate_timeframe(timeframe)
        effective_end = _to_utc_datetime(end) if end else datetime.now(timezone.utc)
        if start is not None:
            effective_start = _to_utc_datetime(start)
        else:
            effective_start = ohlcv_dal.default_start_for_timeframe(timeframe)

        needs_warmup = (
            decision_timeframe is not None
            and timeframe != decision_timeframe
            and warmup.get(timeframe, 0) > 0
            and start is not None
        )
        if needs_warmup:
            effective_start = compute_warmup_start(
                effective_start,
                timeframe,
                warmup[timeframe],
                earliest=ohlcv_dal.default_start_for_timeframe(timeframe),
            )

        bars, _ = await ohlcv_dal.get_bars_with_resample(
            session,
            instrument_id,
            timeframe,
            source=None,
            start=effective_start,
            end=effective_end,
            limit=10_000,
            fetch_tail=False,
        )
        result[timeframe] = sorted(bars, key=lambda bar: bar["time"])

    return result
