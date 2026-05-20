"""Walk-forward Monte Carlo backtest engine."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import numpy as np
import pandas as pd

from dtos.simulation_dto import CalibratedModelParams
from features.backtesting.metrics import compile_all_metrics
from features.backtesting.runner import _compute_buy_hold_curve
from features.quantitative_engine.blended_prob import run_blended_step_prob
from features.quantitative_engine.calibration_service import (
    calibrate_from_prices,
    min_calibration_price_bars,
    _timeframe_to_dt,
)
from features.quantitative_engine.jump_diffusion import JumpDistParams, JumpParams
from features.quantitative_engine.merton_jump_diffusion import MertonParams, run_merton_simulation
from features.quantitative_engine.mc_combo import AlgoComboLeg, generate_combo_actions
from features.quantitative_engine.monte_carlo import VasicekParams, run_simulation
from features.quantitative_engine.ou_deviation import OuDeviationParams, run_single_step_ou_prob
from features.quantitative_engine.mc_features import McFeatureRow, build_feature_row
from features.quantitative_engine.mc_mtf import (
    MtfBarContext,
    build_mtf_context_series,
    mtf_allows_buy,
)
from features.quantitative_engine.ml.regime_model import RegimeModelInference
from features.quantitative_engine.ml.surrogate_model import SurrogateModelInference
from features.quantitative_engine.ml.threshold_model import (
    ThresholdModelInference,
    expanding_percentile_thresholds,
)
from features.quantitative_engine.regime_weight import calc_adx, trend_weight_from_adx
from utils.logging import get_logger
from utils.time_utils import to_utc

logger = get_logger(__name__)

MAX_EVAL_BARS = 1000
MIN_CALIBRATION_BARS = 30
DEFAULT_FEES = 0.001
MIN_PROBS_FOR_SUGGESTIONS = 10
MIN_THRESHOLD_GAP = 0.03

ModelType = Literal["vasicek", "merton", "ou_deviation", "blended"]
SignalAction = Literal["BUY", "SELL", "FLAT"]
ThresholdMode = Literal["static", "ml_dynamic", "suggested_percentile"]
RegimeMode = Literal["adx", "ml"]
DEFAULT_OU_MA_WINDOW = 20
DEFAULT_ADX_PERIOD = 14
DEFAULT_ADX_TREND_THRESHOLD = 25.0
DEFAULT_REGIME_MIN_TREND_WEIGHT = 0.3
DEFAULT_STRUCTURE_MAX_TREND_WEIGHT = 0.7
DEFAULT_ADX_LOW = 15.0


@dataclass
class McBacktestConfig:
    timeframe: str
    start_date: datetime
    end_date: datetime
    model_type: ModelType
    calibration_lookback_days: int
    num_paths: int
    buy_threshold: float
    sell_threshold: float
    initial_capital: float = 1000.0
    prob_smoothing_bars: int = 0
    entry_confirmation_bars: int = 1
    min_hold_bars: int = 0
    cooldown_bars: int = 0
    ou_ma_window: int = DEFAULT_OU_MA_WINDOW
    adx_period: int = DEFAULT_ADX_PERIOD
    adx_trend_threshold: float = DEFAULT_ADX_TREND_THRESHOLD
    combo_enabled: bool = False
    combination_mode: str = "and"
    threshold: float = 0.5
    mc_leg_weight: float = 1.0
    algo_strategies: list[AlgoComboLeg] | None = None
    regime_timeframe: str | None = None
    structure_timeframe: str | None = None
    mtf_gate_enabled: bool = False
    regime_min_trend_weight: float = DEFAULT_REGIME_MIN_TREND_WEIGHT
    structure_veto_enabled: bool = False
    structure_max_trend_weight: float = DEFAULT_STRUCTURE_MAX_TREND_WEIGHT
    threshold_mode: ThresholdMode = "static"
    ml_threshold_model_path: str | None = None
    regime_mode: RegimeMode = "adx"
    ml_regime_model_path: str | None = None
    use_surrogate: bool = False
    ml_surrogate_model_path: str | None = None
    surrogate_sample_pct: float = 0.05


@dataclass
class StepProbResult:
    prob: float
    prob_trend: float | None = None
    prob_reversion: float | None = None
    regime_weight: float | None = None


@dataclass
class WalkForwardCollection:
    raw_probs: list[StepProbResult | None]
    mtf_contexts: list[MtfBarContext]
    feature_rows: list[McFeatureRow | None]
    forward_returns: list[float | None]


@dataclass
class McBacktestResult:
    metrics: dict
    equity_curve: list[dict]
    buy_hold_curve: list[dict]
    trade_log: list[dict]
    execution_log: list[dict]
    signal_log: list[dict]
    zone_stats: dict
    bars_evaluated: int
    duration_ms: float
    combo_signals: list[dict] | None = None
    combined_signal_timeline: list[dict] | None = None


def mc_config_from_request(
    request,
    calibration_lookback_days: int,
    algo_strategies: list[AlgoComboLeg] | None = None,
) -> McBacktestConfig:
    """Build McBacktestConfig from API request DTO."""
    return McBacktestConfig(
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        model_type=request.model_type,
        calibration_lookback_days=calibration_lookback_days,
        num_paths=request.num_paths,
        buy_threshold=request.buy_threshold,
        sell_threshold=request.sell_threshold,
        initial_capital=request.initial_capital,
        prob_smoothing_bars=request.prob_smoothing_bars,
        entry_confirmation_bars=request.entry_confirmation_bars,
        min_hold_bars=request.min_hold_bars,
        cooldown_bars=request.cooldown_bars,
        ou_ma_window=request.ou_ma_window,
        adx_period=request.adx_period,
        adx_trend_threshold=request.adx_trend_threshold,
        combo_enabled=request.combo_enabled,
        combination_mode=request.combination_mode,
        threshold=request.threshold,
        mc_leg_weight=request.mc_leg_weight,
        algo_strategies=algo_strategies,
        regime_timeframe=request.regime_timeframe,
        structure_timeframe=request.structure_timeframe,
        mtf_gate_enabled=request.mtf_gate_enabled,
        regime_min_trend_weight=request.regime_min_trend_weight,
        structure_veto_enabled=request.structure_veto_enabled,
        structure_max_trend_weight=request.structure_max_trend_weight,
        threshold_mode=request.threshold_mode,
        ml_threshold_model_path=request.ml_threshold_model_path,
        regime_mode=request.regime_mode,
        ml_regime_model_path=request.ml_regime_model_path,
        use_surrogate=request.use_surrogate,
        ml_surrogate_model_path=request.ml_surrogate_model_path,
        surrogate_sample_pct=request.surrogate_sample_pct,
    )


def _timeframe_to_periods_per_year(timeframe: str) -> int:
    mapping = {
        "5m": 252 * 78,
        "15m": 252 * 26,
        "30m": 252 * 13,
        "1h": int(252 * 6.5),
        "4h": int(252 * 1.625),
        "1d": 252,
        "1w": 52,
    }
    return mapping.get(timeframe, 252)


def evaluate_mc_signal(
    prob: float,
    in_position: bool,
    buy: float,
    sell: float,
) -> SignalAction:
    """Map prob-positive to a trading action given position state."""
    if not in_position:
        return "BUY" if prob >= buy else "FLAT"
    if prob < sell:
        return "SELL"
    return "FLAT"


def _to_internal_vasicek(dto) -> VasicekParams:
    return VasicekParams(k=dto.k, theta=dto.theta, sigma=dto.sigma, mu=dto.mu)


def _to_internal_merton(dto) -> MertonParams:
    return MertonParams(mu=dto.mu, sigma=dto.sigma)


def _to_internal_jumps(dto) -> JumpParams:
    return JumpParams(
        lambda_up=dto.lambda_up,
        lambda_down=dto.lambda_down,
        up=JumpDistParams(mu=dto.mu_up, sigma=dto.sigma_up),
        down=JumpDistParams(mu=dto.mu_down, sigma=dto.sigma_down),
    )


def _to_internal_ou(dto, s0: float) -> OuDeviationParams:
    ma = dto.ma_level if dto.ma_level > 0 else s0
    x0 = float(np.log(s0 / ma)) if ma > 0 else dto.x0
    return OuDeviationParams(
        kappa=dto.kappa,
        theta=dto.theta,
        sigma=dto.sigma,
        ma_window=dto.ma_window,
        ma_level=ma,
        x0=x0,
    )


def run_single_step_prob(
    params: CalibratedModelParams,
    model_type: ModelType,
    s0: float,
    dt: float,
    n_paths: int,
    adx: float | None = None,
    adx_trend_threshold: float = DEFAULT_ADX_TREND_THRESHOLD,
    w_trend_override: float | None = None,
) -> StepProbResult:
    """Run a 1-step MC simulation and return prob with optional blend diagnostics."""
    jumps = _to_internal_jumps(params.jumps)
    if model_type == "blended":
        if adx is None:
            raise ValueError("ADX required for blended model")
        blended = run_blended_step_prob(
            params, s0, dt, n_paths, adx,
            adx_high=adx_trend_threshold,
            w_trend_override=w_trend_override,
        )
        return StepProbResult(
            prob=blended.prob_effective,
            prob_trend=blended.prob_trend,
            prob_reversion=blended.prob_reversion,
            regime_weight=blended.regime_weight,
        )
    if model_type == "ou_deviation":
        if params.ou_deviation is None:
            raise ValueError("OU deviation params not available")
        ou = _to_internal_ou(params.ou_deviation, s0)
        prob = run_single_step_ou_prob(ou, jumps, s0, dt, n_paths)
        return StepProbResult(prob=prob, prob_reversion=prob)
    if model_type == "merton":
        if params.merton is None:
            raise ValueError("Merton params not available")
        merton = _to_internal_merton(params.merton)
        result = run_merton_simulation(merton, jumps, s0, dt, steps=1, n_paths=n_paths)
        prob = result.stats.prob_positive_return
        return StepProbResult(prob=prob, prob_trend=prob)
    vasicek = _to_internal_vasicek(params.vasicek)
    result = run_simulation(vasicek, jumps, s0, dt, steps=1, n_paths=n_paths)
    prob = result.stats.prob_positive_return
    return StepProbResult(prob=prob)


def _calibration_window_start(bar_time: datetime, lookback_days: int) -> datetime:
    return bar_time - timedelta(days=lookback_days)


def _slice_calibration_df(
    full_df: pd.DataFrame, bar_time: datetime, lookback_days: int,
) -> pd.DataFrame:
    cal_start = _calibration_window_start(bar_time, lookback_days)
    times = pd.to_datetime(full_df["time"], utc=True)
    bar_ts = pd.Timestamp(to_utc(bar_time))
    cal_ts = pd.Timestamp(to_utc(cal_start))
    mask = (times >= cal_ts) & (times <= bar_ts)
    return full_df.loc[mask]


def _min_calibration_bars(config: McBacktestConfig) -> int:
    return min_calibration_price_bars(config.model_type, config.ou_ma_window)


def _smooth_probs(raw_probs: list[StepProbResult | None], window: int) -> list[float | None]:
    """Simple moving average of prob series; window=0 disables smoothing."""
    if window <= 0:
        return [p.prob if p is not None else None for p in raw_probs]
    prob_values = [p.prob if p is not None else None for p in raw_probs]
    smoothed: list[float | None] = []
    for i, prob in enumerate(prob_values):
        if prob is None:
            smoothed.append(None)
            continue
        window_vals = [
            v for v in prob_values[max(0, i - window + 1): i + 1] if v is not None
        ]
        smoothed.append(sum(window_vals) / len(window_vals) if window_vals else None)
    return smoothed


def _resolve_thresholds_for_bar(
    config: McBacktestConfig,
    feature_row: McFeatureRow | None,
    prior_probs: list[float],
    threshold_model: ThresholdModelInference | None,
) -> tuple[float, float]:
    """Per-bar buy/sell thresholds (walk-forward safe for suggested_percentile)."""
    if config.threshold_mode == "ml_dynamic" and threshold_model and threshold_model.is_loaded:
        if feature_row is not None:
            return threshold_model.predict(feature_row)
    if config.threshold_mode == "suggested_percentile":
        return expanding_percentile_thresholds(
            prior_probs, config.buy_threshold, config.sell_threshold,
        )
    return config.buy_threshold, config.sell_threshold


def _resolve_filtered_action(
    effective_prob: float | None,
    in_position: bool,
    bars_in_position: int,
    bars_since_sell: int,
    consecutive_entry_bars: int,
    config: McBacktestConfig,
    buy_threshold: float,
    sell_threshold: float,
    mtf_ctx: MtfBarContext | None = None,
) -> tuple[SignalAction, int]:
    """Apply entry filters; returns action and updated consecutive entry bar count."""
    if effective_prob is None:
        return "FLAT", 0

    if not in_position:
        if bars_since_sell < config.cooldown_bars:
            return "FLAT", 0
        if effective_prob >= buy_threshold:
            if not mtf_allows_buy(
                mtf_ctx,
                config.model_type,
                config.mtf_gate_enabled,
                config.regime_min_trend_weight,
                config.structure_veto_enabled,
                config.structure_max_trend_weight,
            ):
                return "FLAT", 0
            streak = consecutive_entry_bars + 1
            if streak >= config.entry_confirmation_bars:
                return "BUY", 0
            return "FLAT", streak
        return "FLAT", 0

    if bars_in_position < config.min_hold_bars:
        return "FLAT", 0
    if effective_prob < sell_threshold:
        return "SELL", 0
    return "FLAT", 0


def _extract_signal_probs(signal_log: list[dict]) -> list[float]:
    """Prefer effective_prob (post-smoothing) when available."""
    probs: list[float] = []
    for entry in signal_log:
        val = entry.get("effective_prob")
        if val is None:
            val = entry.get("prob_positive")
        if val is not None:
            probs.append(float(val))
    return probs


def compute_prob_distribution_stats(signal_log: list[dict]) -> dict:
    """Percentiles and p75/p25 suggested thresholds from the observed prob series."""
    empty = {
        "prob_min": 0.0,
        "prob_p25": 0.0,
        "prob_median": 0.0,
        "prob_p75": 0.0,
        "prob_max": 0.0,
        "suggested_buy_threshold": None,
        "suggested_sell_threshold": None,
    }
    probs = _extract_signal_probs(signal_log)
    if not probs:
        return empty

    arr = np.array(probs, dtype=float)
    prob_min = float(np.min(arr))
    prob_p25 = float(np.percentile(arr, 25))
    prob_median = float(np.percentile(arr, 50))
    prob_p75 = float(np.percentile(arr, 75))
    prob_max = float(np.max(arr))

    suggested_buy: float | None = None
    suggested_sell: float | None = None
    if len(probs) >= MIN_PROBS_FOR_SUGGESTIONS:
        buy = prob_p75
        sell = prob_p25
        if buy - sell < MIN_THRESHOLD_GAP:
            mid = prob_median
            buy = mid + MIN_THRESHOLD_GAP / 2
            sell = mid - MIN_THRESHOLD_GAP / 2
        buy = round(min(max(buy, 0.01), 0.99), 2)
        sell = round(min(max(sell, 0.01), 0.99), 2)
        if sell >= buy:
            sell = max(0.01, round(buy - MIN_THRESHOLD_GAP, 2))
        suggested_buy = buy
        suggested_sell = sell

    return {
        "prob_min": round(prob_min, 4),
        "prob_p25": round(prob_p25, 4),
        "prob_median": round(prob_median, 4),
        "prob_p75": round(prob_p75, 4),
        "prob_max": round(prob_max, 4),
        "suggested_buy_threshold": suggested_buy,
        "suggested_sell_threshold": suggested_sell,
    }


def compute_prob_zone_stats(
    signal_log: list[dict],
    buy_threshold: float,
    sell_threshold: float,
) -> dict:
    """Fraction of bars in entry / exit / middle prob zones."""
    probs = [s["prob_positive"] for s in signal_log if s.get("prob_positive") is not None]
    if not probs:
        return {
            "entry_zone_pct": 0.0,
            "exit_zone_pct": 0.0,
            "middle_zone_pct": 0.0,
            "bars_with_prob": 0,
        }
    n = len(probs)
    entry = sum(1 for p in probs if p >= buy_threshold)
    exit_ct = sum(1 for p in probs if p < sell_threshold)
    middle = sum(1 for p in probs if sell_threshold <= p < buy_threshold)
    return {
        "entry_zone_pct": round(entry / n * 100, 1),
        "exit_zone_pct": round(exit_ct / n * 100, 1),
        "middle_zone_pct": round(middle / n * 100, 1),
        "bars_with_prob": n,
    }


def _load_ml_models(config: McBacktestConfig) -> tuple[
    ThresholdModelInference | None,
    RegimeModelInference | None,
    SurrogateModelInference | None,
]:
    threshold_model = None
    if config.threshold_mode == "ml_dynamic" and config.ml_threshold_model_path:
        threshold_model = ThresholdModelInference(config.ml_threshold_model_path)
    regime_model = None
    if config.regime_mode == "ml" and config.ml_regime_model_path:
        regime_model = RegimeModelInference(config.ml_regime_model_path)
    surrogate = None
    if config.use_surrogate and config.ml_surrogate_model_path:
        surrogate = SurrogateModelInference(config.ml_surrogate_model_path)
    return threshold_model, regime_model, surrogate


def _resolve_regime_adx_and_weight(
    config: McBacktestConfig,
    adx_exec: float,
    mtf_ctx: MtfBarContext,
    feature_row: McFeatureRow | None,
    regime_model: RegimeModelInference | None,
) -> tuple[float, float | None]:
    """ADX for blended + optional ML w_trend override."""
    adx_for_blend = adx_exec
    if mtf_ctx.regime_adx is not None:
        adx_for_blend = mtf_ctx.regime_adx
    w_override: float | None = None
    if config.regime_mode == "ml" and regime_model and regime_model.is_loaded and feature_row:
        w_override = regime_model.predict_w_trend(feature_row, adx_for_blend)
    elif mtf_ctx.regime_w_trend is not None and config.regime_timeframe:
        w_override = mtf_ctx.regime_w_trend
    return adx_for_blend, w_override


def _collect_walk_forward(
    full_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    config: McBacktestConfig,
) -> WalkForwardCollection:
    dt = _timeframe_to_dt(config.timeframe)
    min_bars = _min_calibration_bars(config)
    adx_series = calc_adx(
        full_df["high"].astype(float),
        full_df["low"].astype(float),
        full_df["close"].astype(float),
        period=config.adx_period,
    )
    adx_by_time = dict(zip(full_df["time"], adx_series))
    mtf_contexts = build_mtf_context_series(
        full_df,
        eval_df,
        config.regime_timeframe,
        config.structure_timeframe,
        config.adx_period,
        DEFAULT_ADX_LOW,
        config.adx_trend_threshold,
    )
    mtf_gate = config.mtf_gate_enabled or bool(config.regime_timeframe)

    _, regime_model, surrogate = _load_ml_models(config)
    closes = eval_df["close"].astype(float).tolist()
    raw_probs: list[StepProbResult | None] = []
    feature_rows: list[McFeatureRow | None] = []
    forward_returns: list[float | None] = []
    prior_probs: list[float] = []
    rng = np.random.default_rng(42)
    for i, (_, row) in enumerate(eval_df.iterrows()):
        bar_time = row["time"]
        mtf_ctx = mtf_contexts[i]
        fwd_ret = None
        if i + 1 < len(closes) and closes[i] > 0:
            fwd_ret = (closes[i + 1] - closes[i]) / closes[i]
        forward_returns.append(fwd_ret)

        cal_df = _slice_calibration_df(full_df, bar_time, config.calibration_lookback_days)
        if len(cal_df) < min_bars:
            raw_probs.append(None)
            feature_rows.append(None)
            continue

        prices = cal_df["close"].to_numpy(dtype=float)
        cal_start = cal_df["time"].iloc[0]
        params = calibrate_from_prices(
            prices,
            config.timeframe,
            cal_start,
            bar_time,
            ou_ma_window=config.ou_ma_window,
            model_type=config.model_type,
        )
        s0 = float(row["close"])
        adx_val = float(adx_by_time.get(bar_time, float("nan")))
        w_exec = trend_weight_from_adx(
            adx_val, low=DEFAULT_ADX_LOW, high=config.adx_trend_threshold,
        )
        feat_row = build_feature_row(
            i, cal_df, None, None, None, mtf_ctx, adx_val, w_exec, prior_probs,
        )
        adx_blend, w_override = _resolve_regime_adx_and_weight(
            config, adx_val, mtf_ctx, feat_row, regime_model,
        )

        run_true_mc = (
            surrogate is None
            or not surrogate.is_loaded
            or rng.random() < config.surrogate_sample_pct
        )
        try:
            if not run_true_mc and surrogate is not None:
                prob = surrogate.predict_prob(feat_row)
                step = StepProbResult(
                    prob=prob,
                    prob_trend=prob if config.model_type == "merton" else None,
                    prob_reversion=prob if config.model_type == "ou_deviation" else None,
                    regime_weight=w_override,
                )
            else:
                step = run_single_step_prob(
                    params,
                    config.model_type,
                    s0,
                    dt,
                    config.num_paths,
                    adx=adx_blend if config.model_type == "blended" else None,
                    adx_trend_threshold=config.adx_trend_threshold,
                    w_trend_override=w_override if config.model_type == "blended" else None,
                )
                if surrogate is not None and surrogate.is_loaded:
                    sur_prob = surrogate.predict_prob(feat_row)
                    if abs(sur_prob - step.prob) > 0.15:
                        logger.warning(
                            "surrogate_drift",
                            bar=str(bar_time),
                            mc_prob=round(step.prob, 4),
                            sur_prob=round(sur_prob, 4),
                        )
        except ValueError:
            raw_probs.append(None)
            feature_rows.append(None)
            continue

        feat_row = build_feature_row(
            i,
            cal_df,
            step.prob,
            step.prob_trend,
            step.prob_reversion,
            mtf_ctx,
            adx_val,
            w_exec,
            prior_probs,
        )
        prior_probs.append(step.prob)
        raw_probs.append(step)
        feature_rows.append(feat_row)

    return WalkForwardCollection(
        raw_probs=raw_probs,
        mtf_contexts=mtf_contexts,
        feature_rows=feature_rows,
        forward_returns=forward_returns,
    )


def _collect_raw_probs(
    full_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    config: McBacktestConfig,
) -> list[StepProbResult | None]:
    return _collect_walk_forward(full_df, eval_df, config).raw_probs


def _collect_walk_forward_rows(
    full_df: pd.DataFrame,
    config: McBacktestConfig,
) -> list[dict]:
    """Export feature rows with labels for offline ML training."""
    from features.quantitative_engine.mc_features import FEATURE_NAMES

    full_df = full_df.sort_values("time").reset_index(drop=True)
    full_df["time"] = pd.to_datetime(full_df["time"], utc=True)
    start_ts = pd.Timestamp(to_utc(config.start_date))
    end_ts = pd.Timestamp(to_utc(config.end_date))
    eval_df = full_df.loc[
        (full_df["time"] >= start_ts) & (full_df["time"] <= end_ts)
    ].reset_index(drop=True)
    coll = _collect_walk_forward(full_df, eval_df, config)
    rows: list[dict] = []
    for i, (_, row) in enumerate(eval_df.iterrows()):
        feat = coll.feature_rows[i]
        if feat is None:
            continue
        out = {k: feat.features[k] for k in FEATURE_NAMES}
        out["time"] = str(row["time"])
        step = coll.raw_probs[i]
        out["label_prob"] = step.prob if step else 0.5
        out["label_w_trend"] = step.regime_weight if step and step.regime_weight is not None else 0.5
        out["label_buy_threshold"] = config.buy_threshold
        out["label_sell_threshold"] = config.sell_threshold
        fwd = coll.forward_returns[i]
        if fwd is not None and step:
            if fwd > 0:
                out["label_buy_threshold"] = max(0.01, step.prob - 0.02)
            else:
                out["label_sell_threshold"] = min(0.99, step.prob + 0.02)
        rows.append(out)
    return rows


def _build_prob_signal_log(
    eval_df: pd.DataFrame,
    raw_probs: list[StepProbResult | None],
    effective_probs: list[float | None],
    mtf_contexts: list[MtfBarContext] | None = None,
    bar_thresholds: list[tuple[float, float]] | None = None,
) -> list[dict]:
    """Walk-forward prob diagnostics per eval bar (signal filled by caller)."""
    signal_log: list[dict] = []
    for i, (_, row) in enumerate(eval_df.iterrows()):
        raw = raw_probs[i]
        effective = effective_probs[i]
        signal_entry: dict = {
            "time": str(row["time"]),
            "prob_positive": round(raw.prob, 6) if raw is not None else None,
            "effective_prob": round(effective, 6) if effective is not None else None,
            "signal": "FLAT",
        }
        if raw is not None:
            if raw.prob_trend is not None:
                signal_entry["prob_trend"] = round(raw.prob_trend, 6)
            if raw.prob_reversion is not None:
                signal_entry["prob_reversion"] = round(raw.prob_reversion, 6)
            if raw.regime_weight is not None:
                signal_entry["regime_weight"] = round(raw.regime_weight, 6)
        if mtf_contexts and i < len(mtf_contexts):
            ctx = mtf_contexts[i]
            if ctx.regime_w_trend is not None:
                signal_entry["regime_w_trend_htf"] = round(ctx.regime_w_trend, 6)
        if bar_thresholds and i < len(bar_thresholds):
            buy_t, sell_t = bar_thresholds[i]
            signal_entry["buy_threshold_effective"] = round(buy_t, 4)
            signal_entry["sell_threshold_effective"] = round(sell_t, 4)
        signal_log.append(signal_entry)
    return signal_log


def _generate_mc_only_actions(
    effective_probs: list[float | None],
    config: McBacktestConfig,
    collection: WalkForwardCollection,
    threshold_model: ThresholdModelInference | None,
) -> list[SignalAction]:
    """Resolve per-bar actions from MC prob thresholds and entry filters."""
    actions: list[SignalAction] = []
    in_position = False
    bars_in_position = 0
    bars_since_sell = config.cooldown_bars
    consecutive_entry_bars = 0
    prior_probs: list[float] = []
    mtf_gate = config.mtf_gate_enabled or bool(config.regime_timeframe)

    for i, effective in enumerate(effective_probs):
        feat = collection.feature_rows[i] if i < len(collection.feature_rows) else None
        buy_t, sell_t = _resolve_thresholds_for_bar(config, feat, prior_probs, threshold_model)
        if effective is not None:
            prior_probs.append(effective)
        mtf_ctx = collection.mtf_contexts[i] if i < len(collection.mtf_contexts) else None
        cfg_gate = McBacktestConfig(**{**config.__dict__, "mtf_gate_enabled": mtf_gate})
        action, consecutive_entry_bars = _resolve_filtered_action(
            effective,
            in_position,
            bars_in_position,
            bars_since_sell,
            consecutive_entry_bars,
            cfg_gate,
            buy_t,
            sell_t,
            mtf_ctx,
        )
        actions.append(action)
        if action == "BUY":
            in_position = True
            bars_in_position = 0
            bars_since_sell = 0
        elif action == "SELL":
            in_position = False
            bars_in_position = 0
            bars_since_sell = 0
        else:
            if in_position:
                bars_in_position += 1
            bars_since_sell += 1
    return actions


def _bar_threshold_series(
    config: McBacktestConfig,
    collection: WalkForwardCollection,
    effective_probs: list[float | None],
    threshold_model: ThresholdModelInference | None,
) -> list[tuple[float, float]]:
    prior: list[float] = []
    out: list[tuple[float, float]] = []
    for i, eff in enumerate(effective_probs):
        feat = collection.feature_rows[i] if i < len(collection.feature_rows) else None
        buy_t, sell_t = _resolve_thresholds_for_bar(config, feat, prior, threshold_model)
        out.append((buy_t, sell_t))
        if eff is not None:
            prior.append(eff)
    return out


def _generate_signals(
    full_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    config: McBacktestConfig,
) -> tuple[list[SignalAction], list[dict], list[dict], list[dict]]:
    """Walk-forward: calibrate + 1-step MC at each eval bar."""
    collection = _collect_walk_forward(full_df, eval_df, config)
    raw_probs = collection.raw_probs
    effective_probs = _smooth_probs(raw_probs, config.prob_smoothing_bars)
    threshold_model, _, _ = _load_ml_models(config)
    bar_thresholds = _bar_threshold_series(
        config, collection, effective_probs, threshold_model,
    )
    signal_log = _build_prob_signal_log(
        eval_df, raw_probs, effective_probs, collection.mtf_contexts, bar_thresholds,
    )
    combo_signals: list[dict] = []
    combined_timeline: list[dict] = []

    if config.combo_enabled and config.algo_strategies:
        actions, combo_signals, combined_timeline = generate_combo_actions(
            full_df,
            eval_df,
            effective_probs,
            config.buy_threshold,
            config.sell_threshold,
            config.timeframe,
            config.algo_strategies,
            config.combination_mode,
            config.mc_leg_weight,
            config.threshold,
            config.entry_confirmation_bars,
            config.min_hold_bars,
            config.cooldown_bars,
        )
    else:
        actions = _generate_mc_only_actions(
            effective_probs, config, collection, threshold_model,
        )

    for i, action in enumerate(actions):
        signal_log[i]["signal"] = action

    return actions, signal_log, combo_signals, combined_timeline


def simulate_portfolio(
    eval_df: pd.DataFrame,
    actions: list[SignalAction],
    initial_capital: float,
    fees: float = DEFAULT_FEES,
) -> tuple[list[dict], list[dict], list[dict], pd.Series, dict | None, float]:
    """Long-only all-in portfolio; signals execute at next bar open.

    Returns equity_curve, closed_trade_log, execution_log, equity_series,
    open_trade (if still long), shares.
    """
    cash = initial_capital
    shares = 0.0
    in_position = False
    equity_curve: list[dict] = []
    closed_trade_log: list[dict] = []
    execution_log: list[dict] = []
    open_trade: dict | None = None

    times = eval_df["time"].tolist()
    opens = eval_df["open"].astype(float).tolist()
    closes = eval_df["close"].astype(float).tolist()

    for i, bar_time in enumerate(times):
        if i > 0:
            action = actions[i - 1]
            price = opens[i]
            if action == "BUY" and not in_position and cash > 0:
                invested = cash * (1 - fees)
                shares = invested / price
                cash = 0.0
                in_position = True
                open_trade = {"entry_time": str(bar_time), "entry_price": price, "entry_cost": invested}
            elif action == "SELL" and in_position and shares > 0:
                proceeds = shares * price * (1 - fees)
                entry_cost = open_trade["entry_cost"] if open_trade else shares * price
                pnl = proceeds - entry_cost
                ret = pnl / entry_cost if entry_cost else 0.0
                closed_trade_log.append({
                    "entry_time": open_trade["entry_time"] if open_trade else "",
                    "exit_time": str(bar_time),
                    "direction": "long",
                    "entry_price": open_trade["entry_price"] if open_trade else price,
                    "exit_price": price,
                    "pnl": round(pnl, 4),
                    "return_pct": round(ret, 6),
                })
                cash = proceeds
                shares = 0.0
                in_position = False
                open_trade = None

        equity = cash + shares * closes[i]
        equity_curve.append({"time": str(bar_time), "value": round(equity, 4)})

        if i > 0:
            action = actions[i - 1]
            if action == "BUY" and in_position and open_trade and str(bar_time) == open_trade["entry_time"]:
                execution_log.append({
                    "time": str(bar_time),
                    "side": "buy",
                    "price": round(opens[i], 4),
                    "equity": round(equity, 4),
                })
            elif action == "SELL" and not in_position and closed_trade_log:
                if closed_trade_log[-1].get("exit_time") == str(bar_time):
                    execution_log.append({
                        "time": str(bar_time),
                        "side": "sell",
                        "price": round(opens[i], 4),
                        "equity": round(equity, 4),
                    })

    equity_series = pd.Series([p["value"] for p in equity_curve])
    return equity_curve, closed_trade_log, execution_log, equity_series, open_trade, shares


def _append_open_trade_row(
    closed_trade_log: list[dict],
    open_trade: dict | None,
    shares: float,
    last_close: float,
) -> list[dict]:
    """Build display trade_log including mark-to-market open position."""
    if open_trade is None or shares <= 0:
        return list(closed_trade_log)

    entry_cost = open_trade["entry_cost"]
    mtm_value = shares * last_close
    pnl = mtm_value - entry_cost
    ret = pnl / entry_cost if entry_cost else 0.0
    open_row = {
        "entry_time": open_trade["entry_time"],
        "exit_time": None,
        "direction": "long",
        "entry_price": open_trade["entry_price"],
        "exit_price": None,
        "pnl": round(pnl, 4),
        "return_pct": round(ret, 6),
        "status": "open",
    }
    return closed_trade_log + [open_row]


def run_mc_backtest(full_df: pd.DataFrame, config: McBacktestConfig) -> McBacktestResult:
    """Execute walk-forward MC backtest over the configured date range."""
    t0 = time.perf_counter()

    if full_df.empty:
        raise ValueError("No OHLCV data available for backtest")

    full_df = full_df.sort_values("time").reset_index(drop=True)
    full_df = full_df.copy()
    full_df["time"] = pd.to_datetime(full_df["time"], utc=True)
    start_ts = pd.Timestamp(to_utc(config.start_date))
    end_ts = pd.Timestamp(to_utc(config.end_date))
    mask = (full_df["time"] >= start_ts) & (full_df["time"] <= end_ts)
    eval_df = full_df.loc[mask].reset_index(drop=True)

    if eval_df.empty:
        raise ValueError("No bars in the selected simulation period")

    if len(eval_df) > MAX_EVAL_BARS:
        raise ValueError(
            f"Simulation period has {len(eval_df)} bars; maximum is {MAX_EVAL_BARS}. "
            "Shorten the date range or use a coarser timeframe."
        )

    actions, signal_log, combo_signals, combined_timeline = _generate_signals(
        full_df, eval_df, config,
    )
    zone_stats = compute_prob_zone_stats(
        signal_log, config.buy_threshold, config.sell_threshold,
    )
    zone_stats.update(compute_prob_distribution_stats(signal_log))
    equity_curve, closed_trades, execution_log, equity_series, open_trade, shares = simulate_portfolio(
        eval_df, actions, config.initial_capital,
    )
    last_close = float(eval_df["close"].iloc[-1])
    display_trade_log = _append_open_trade_row(closed_trades, open_trade, shares, last_close)

    close = eval_df.set_index("time")["close"].astype(float)
    buy_hold_curve = _compute_buy_hold_curve(close, config.initial_capital)
    returns = equity_series.pct_change().fillna(0.0)
    periods = _timeframe_to_periods_per_year(config.timeframe)
    metrics = compile_all_metrics(returns, equity_series, closed_trades, periods_per_year=periods)
    metrics["excess_return"] = _compute_excess_return(metrics, buy_hold_curve)

    duration_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "mc_backtest_complete",
        bars=len(eval_df),
        trades=metrics.get("num_trades", 0),
        total_return=round(metrics.get("total_return", 0), 4),
        duration_ms=round(duration_ms, 2),
    )

    return McBacktestResult(
        metrics=metrics,
        equity_curve=equity_curve,
        buy_hold_curve=buy_hold_curve,
        trade_log=display_trade_log,
        execution_log=execution_log,
        signal_log=signal_log,
        zone_stats=zone_stats,
        bars_evaluated=len(eval_df),
        duration_ms=duration_ms,
        combo_signals=combo_signals or None,
        combined_signal_timeline=combined_timeline or None,
    )


def _compute_excess_return(metrics: dict, buy_hold_curve: list[dict]) -> float:
    """Strategy total return minus buy-and-hold over the same period."""
    if not buy_hold_curve:
        return float(metrics.get("total_return", 0.0))
    start_val = float(buy_hold_curve[0]["value"])
    end_val = float(buy_hold_curve[-1]["value"])
    bh_return = (end_val - start_val) / start_val if start_val else 0.0
    return float(metrics.get("total_return", 0.0)) - bh_return
