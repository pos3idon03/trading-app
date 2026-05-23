from typing import Any, Optional

from features.backtesting.indicators import compute_ema, compute_rsi, compute_sma
from features.backtesting.strategies.registry import ENSEMBLE_LEG_STRATEGIES, STRATEGY_CATALOG

_SIGNAL_ENCODING = {"sell": -1.0, "hold": 0.0, "buy": 1.0}


def _validate_strategy_ids(strategy_ids: list[str]) -> None:
    unknown = [sid for sid in strategy_ids if sid not in STRATEGY_CATALOG]
    if unknown:
        raise ValueError(f"Unknown strategy ids: {', '.join(unknown)}")
    ineligible = [sid for sid in strategy_ids if sid not in ENSEMBLE_LEG_STRATEGIES]
    if ineligible:
        raise ValueError(
            f"Strategy ids not eligible as ML features: {', '.join(ineligible)}"
        )


def _continuous_features(
    strategy_id: str,
    bars: list[dict],
    params: dict[str, Any],
    index: int,
) -> list[Optional[float]]:
    closes = [float(b["close"]) for b in bars]
    if strategy_id in ("sma_crossover", "ema_crossover"):
        fast_key = "fast_period"
        slow_key = "slow_period"
        if strategy_id == "sma_crossover":
            fast = compute_sma(closes, int(params[fast_key]))
            slow = compute_sma(closes, int(params[slow_key]))
        else:
            fast = compute_ema(closes, int(params[fast_key]))
            slow = compute_ema(closes, int(params[slow_key]))
        if fast[index] is None or slow[index] is None or slow[index] == 0:
            return [None, None]
        spread = (fast[index] - slow[index]) / slow[index]
        return [float(spread), float(fast[index] / slow[index] - 1.0)]

    if strategy_id == "rsi_reversion":
        rsi = compute_rsi(closes, int(params["period"]))
        value = rsi[index]
        if value is None:
            return [None]
        return [float(value)]

    if strategy_id == "ts_momentum":
        lookback = int(params.get("lookback", 20))
        if index < lookback or closes[index - lookback] == 0:
            return [None]
        momentum = (closes[index] / closes[index - lookback]) - 1.0
        return [float(momentum)]

    return []


def build_strategy_feature_matrix(
    bars: list[dict],
    strategy_ids: list[str],
    strategy_params: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[str], list[Optional[list[float]]], list[str]]:
    if not strategy_ids:
        return [], [None] * len(bars), []

    _validate_strategy_ids(strategy_ids)
    params_by_id = strategy_params or {}
    feature_names: list[str] = []
    column_data: list[list[Optional[float]]] = []
    warnings: list[str] = []

    for strategy_id in strategy_ids:
        meta = STRATEGY_CATALOG[strategy_id]
        params = {**meta["params"], **params_by_id.get(strategy_id, {})}
        min_bars = int(meta.get("min_bars", 1))
        signal_fn = meta["signal_fn"]

        cont_suffixes = ["cont_0", "cont_1"] if strategy_id in ("sma_crossover", "ema_crossover") else ["cont_0"]
        names = [f"strat_{strategy_id}_signal", *[f"strat_{strategy_id}_{s}" for s in cont_suffixes]]
        signal_col: list[Optional[float]] = []
        cont_cols: list[list[Optional[float]]] = [[None] * len(bars) for _ in cont_suffixes]

        for index in range(len(bars)):
            if index < min_bars:
                signal_col.append(None)
                continue
            signal = signal_fn(bars, [], params, index)
            signal_col.append(_SIGNAL_ENCODING.get(signal, 0.0))
            cont_values = _continuous_features(strategy_id, bars, params, index)
            for col_index, suffix in enumerate(cont_suffixes):
                value = cont_values[col_index] if col_index < len(cont_values) else None
                cont_cols[col_index][index] = value
            if any(cont_cols[i][index] is None for i in range(len(cont_suffixes))):
                signal_col[-1] = None

        feature_names.extend(names)
        column_data.append(signal_col)
        column_data.extend(cont_cols)

    rows: list[Optional[list[float]]] = []
    for row_index in range(len(bars)):
        row_values: list[float] = []
        row_complete = True
        for column in column_data:
            value = column[row_index]
            if value is None:
                row_complete = False
                break
            row_values.append(float(value))
        rows.append(row_values if row_complete else None)

    if not rows or all(row is None for row in rows):
        warnings.append("Strategy features could not be built for the selected strategies.")

    return feature_names, rows, warnings
