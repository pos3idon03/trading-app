import type {
  MlHyperparameterSearchResponse,
  MlLabelMode,
  MlModelCatalogItem,
  MlParams,
} from '../api/mlBacktestTypes';
import { FUNDAMENTAL_METRIC_CODES } from '../constants/fundamentalsMetrics';
import { INTRADAY_BAR_LIMIT, INTRADAY_TIMEFRAMES } from '../constants/timeframes';
import { ML_FIELD_LABELS } from './mlBacktestHelp';
import { parseIndicatorGroups, validateIndicatorGroups } from './mlIndicatorGroups';

function parseIndicatorGroupsFromRaw(raw: unknown): string[] {
  return parseIndicatorGroups(raw);
}

export {
  DEFAULT_INDICATOR_GROUPS,
  ML_INDICATOR_GROUPS,
  validateIndicatorGroups,
  formatIndicatorGroupsSummary,
} from './mlIndicatorGroups';

export const FEATURE_WARMUP_BARS = 200;
export const CRYPTO_FEATURE_WARMUP_BARS = 200;

export const WARMUP_BARS_CONSTRAINTS = { min: 50, max: 500 } as const;

export function resolveWarmupBars(params: { warmup_bars?: number }): number {
  const raw = params.warmup_bars ?? FEATURE_WARMUP_BARS;
  return Math.max(
    WARMUP_BARS_CONSTRAINTS.min,
    Math.min(WARMUP_BARS_CONSTRAINTS.max, Math.round(raw)),
  );
}

export const CRYPTO_MACRO_SERIES_IDS = ['T10Y2Y', 'WALCL', 'WTREGEN'];

const TRADING_MINUTES_PER_DAY = 6.5 * 60;
const MIN_TRAIN_BARS = 10;
const MIN_TEST_BARS = 1;

export type WalkForwardParamKey = 'train_bars' | 'test_bars' | 'step_bars' | 'label_horizon';

export const WALK_FORWARD_PARAM_KEYS: WalkForwardParamKey[] = [
  'train_bars',
  'test_bars',
  'step_bars',
  'label_horizon',
];

export const WALK_FORWARD_CONSTRAINTS: Record<
  WalkForwardParamKey,
  { min: number; max: number }
> = {
  train_bars: { min: 10, max: 2000 },
  test_bars: { min: 1, max: 500 },
  step_bars: { min: 1, max: 500 },
  label_horizon: { min: 1, max: 60 },
};

export type WalkForwardParams = Pick<MlParams, WalkForwardParamKey> & {
  warmup_bars?: number;
};

export function pickWalkForwardParams(params: MlParams): WalkForwardParams {
  return {
    warmup_bars: params.warmup_bars,
    train_bars: params.train_bars,
    test_bars: params.test_bars,
    step_bars: params.step_bars,
    label_horizon: params.label_horizon,
  };
}

export const LABEL_SEARCH_HORIZON_OFFSETS = [-4, -2, 0, 2, 4] as const;

/** Literature-aligned defaults for label grid search (mirrors backend catalog). */
export const DEFAULT_LABEL_MODE_BY_MODEL: Record<string, MlLabelMode> = {
  ml_logistic: 'binary',
  ml_random_forest: 'ternary',
  ml_gradient_boosting: 'binary',
  ml_xgboost: 'binary',
  ml_knn: 'binary',
  ml_lstm: 'meta_label',
};

export function labelSearchHorizons(
  center: number,
  min = WALK_FORWARD_CONSTRAINTS.label_horizon.min,
  max = WALK_FORWARD_CONSTRAINTS.label_horizon.max,
): number[] {
  const values = LABEL_SEARCH_HORIZON_OFFSETS.map((offset) => center + offset).filter(
    (h) => h >= min && h <= max,
  );
  return [...new Set(values)].sort((a, b) => a - b);
}

export function barsPerYear(timeframe: string, assetType: string = 'equity'): number {
  if (timeframe === '1d') return assetType === 'crypto' ? 365 : 252;
  if (timeframe === '1w') return 52;
  if (timeframe === '1mo') return 12;

  const minutesMap: Record<string, number> = {
    '1m': 1,
    '5m': 5,
    '15m': 15,
    '30m': 30,
    '1h': 60,
    '4h': 240,
  };
  const bucket = minutesMap[timeframe];
  if (bucket == null) return 252;
  if (assetType === 'crypto') {
    return (24 * 365 * 60) / bucket;
  }
  return 252 * (TRADING_MINUTES_PER_DAY / bucket);
}

export function getCryptoMlPreset(timeframe: string = '1h'): MlParams {
  const wfo = defaultWalkForwardParams(timeframe, 'crypto');
  return {
    ...DEFAULT_ML_PARAMS,
    feature_mode: 'prices_macro',
    macro_series_ids: CRYPTO_MACRO_SERIES_IDS,
    macro_publication_lag_days: { rates: 1 },
    include_news_sentiment: true,
    strategy_feature_ids: [],
    label_mode: 'meta_label',
    base_strategy_id: 'crypto_trend_entry',
    base_strategy_params: { slow_period: 50, rsi_period: 14, rsi_max: 65 },
    profit_atr_mult: 2,
    stop_atr_mult: 1.5,
    max_horizon_bars: 48,
    meta_gate_threshold: 0.65,
    slippage_bps: 5,
    buy_threshold: 0.65,
    sell_threshold: 0.35,
    ...wfo,
  };
}

export function defaultWalkForwardParams(
  timeframe: string,
  assetType: string = 'equity',
): Pick<MlParams, 'train_bars' | 'test_bars' | 'step_bars' | 'label_horizon'> {
  const bpy = barsPerYear(timeframe, assetType);
  if (assetType === 'crypto' && timeframe === '1h') {
    const train = Math.max(MIN_TRAIN_BARS, Math.min(2000, Math.round(bpy / 2)));
    const test = Math.max(MIN_TEST_BARS, Math.min(500, Math.round(bpy / 12)));
    return { train_bars: train, test_bars: test, step_bars: test, label_horizon: 5 };
  }
  let train = Math.max(MIN_TRAIN_BARS, Math.min(2000, Math.round(bpy)));
  let test = Math.max(MIN_TEST_BARS, Math.min(500, Math.round((bpy * 63) / 252)));
  let step = test;
  let labelHorizon = 5;
  if (timeframe === '1w') labelHorizon = 4;
  else if (timeframe === '1mo') labelHorizon = 3;

  if (INTRADAY_TIMEFRAMES.has(timeframe)) {
    const walkForwardBudget = INTRADAY_BAR_LIMIT - FEATURE_WARMUP_BARS - labelHorizon;
    if (train + test > walkForwardBudget) {
      train = Math.max(MIN_TRAIN_BARS, Math.floor(walkForwardBudget * 0.75));
      test = Math.max(MIN_TEST_BARS, walkForwardBudget - train);
      step = Math.min(test, 63);
    }
  }

  return { train_bars: train, test_bars: test, step_bars: step, label_horizon: labelHorizon };
}

export function fitWalkForwardParamsToBarCount(
  barCount: number,
  timeframe: string,
): Pick<MlParams, 'train_bars' | 'test_bars' | 'step_bars' | 'label_horizon'> {
  const ideal = defaultWalkForwardParams(timeframe);
  if (barCount >= minimumBarsRequired(ideal as MlParams)) {
    return ideal;
  }

  const budget = barCount - FEATURE_WARMUP_BARS - ideal.label_horizon;
  if (budget < MIN_TRAIN_BARS + MIN_TEST_BARS) {
    return ideal;
  }

  const train = Math.max(MIN_TRAIN_BARS, Math.floor(budget * 0.75));
  const test = Math.max(MIN_TEST_BARS, budget - train);
  const step = Math.max(1, Math.min(test, ideal.step_bars));
  return { ...ideal, train_bars: train, test_bars: test, step_bars: step };
}

export function resolveWalkForwardParams(
  timeframe: string,
  barCount?: number | null,
  assetType: string = 'equity',
): Pick<MlParams, 'train_bars' | 'test_bars' | 'step_bars' | 'label_horizon'> {
  const ideal = defaultWalkForwardParams(timeframe, assetType);
  if (barCount == null || barCount <= 0) {
    return ideal;
  }
  return fitWalkForwardParamsToBarCount(barCount, timeframe);
}

export const DEFAULT_MACRO_SERIES_IDS = ['DFF', 'DGS2', 'DGS10', 'T10Y2Y', 'CPIAUCSL', 'CPILFESL', 'PCEPI'];

export const ML_EXIT_POLICIES = [
  { value: 'signal_only', label: 'Signal only (legacy)' },
  { value: 'label_horizon', label: 'Max hold = label horizon' },
  { value: 'atr_bracket', label: 'ATR stop / target' },
  { value: 'combined', label: 'Combined (signal + horizon + ATR)' },
] as const;

export type MlExitPolicy = (typeof ML_EXIT_POLICIES)[number]['value'];

export function defaultExitPolicyForLabelMode(labelMode: string): MlExitPolicy {
  return labelMode === 'meta_label' ? 'atr_bracket' : 'label_horizon';
}

export function applyAlignedExitPolicy(params: MlParams): MlParams {
  const policy = defaultExitPolicyForLabelMode(params.label_mode ?? 'binary');
  return {
    ...params,
    exit_policy: policy,
    max_hold_bars:
      policy === 'label_horizon'
        ? params.label_horizon
        : params.max_horizon_bars ?? params.label_horizon,
    profit_atr_mult: params.profit_atr_mult ?? 2,
    stop_atr_mult: params.stop_atr_mult ?? 1.5,
    atr_period: params.atr_period ?? 14,
  };
}

export const ML_FEATURE_MODES = [
  { value: 'prices_only', label: 'Prices only' },
  { value: 'prices_macro', label: 'Prices + macro' },
  { value: 'prices_macro_fundamentals', label: 'Full (prices + macro + fundamentals)' },
] as const;

export function featureModeUsesMacro(featureMode: string): boolean {
  return featureMode === 'prices_macro' || featureMode === 'prices_macro_fundamentals';
}

export const DEFAULT_FUNDAMENTAL_METRICS = [...FUNDAMENTAL_METRIC_CODES];

export const DEFAULT_ML_PARAMS: MlParams = {
  feature_mode: 'prices_only',
  macro_series_ids: DEFAULT_MACRO_SERIES_IDS,
  macro_publication_lag_days: {},
  fundamental_metrics: DEFAULT_FUNDAMENTAL_METRICS,
  fundamental_period_type: 'quarterly',
  context_timeframes: [],
  strategy_feature_ids: [],
  strategy_feature_params: {},
  label_mode: 'binary',
  label_threshold: 0.01,
  label_method: 'endpoint',
  label_horizon: 5,
  warmup_bars: FEATURE_WARMUP_BARS,
  train_bars: 252,
  test_bars: 63,
  step_bars: 63,
  buy_threshold: 0.55,
  sell_threshold: 0.45,
  inference_eval_scope: 'holdout',
  include_news_sentiment: false,
  slippage_bps: 0,
  max_horizon_bars: 48,
  meta_gate_threshold: 0.65,
  random_forest_estimators: 100,
  gradient_boosting_max_iter: 100,
  knn_neighbors: 5,
  xgboost_estimators: 100,
  xgboost_max_depth: 6,
  xgboost_learning_rate: 0.1,
  denoise_method: 'none',
  include_cross_sectional_factors: false,
  include_metadata_features: false,
  dynamic_indicator_selection: false,
  indicator_groups: ['momentum', 'mean_reversion', 'volatility'],
  correlation_prune_threshold: 0.75,
  sizing_method: 'fixed_fraction',
  kelly_fraction: 0.25,
  hrp_lookback_bars: 252,
  rebalance_frequency: 21,
  hrp_linkage_method: 'single',
  lstm_seq_length: 32,
  lstm_hidden_size: 64,
  lstm_num_layers: 2,
  lstm_epochs: 10,
  lstm_dropout: 0.2,
  lstm_learning_rate: 0.001,
  lstm_batch_size: 32,
  profit_atr_mult: 2,
  stop_atr_mult: 1.5,
  atr_period: 14,
  technical_pca_enabled: true,
  technical_pca_variance_threshold: 0.85,
  macro_features_mode: 'changes_only',
  macro_pca_enabled: true,
  macro_pca_variance_threshold: 0.85,
  macro_pca_input_mode: 'changes_only',
  fundamental_features_mode: 'growth_only',
  fundamental_pca_enabled: true,
  fundamental_pca_variance_threshold: 0.85,
  fundamental_pca_input_mode: 'kpi_only',
};

export function parseMlParams(raw: Record<string, unknown>): MlParams {
  const macroIds = raw.macro_series_ids;
  const fundamentalMetrics = raw.fundamental_metrics;
  const periodType = raw.fundamental_period_type;
  return {
    feature_mode: String(raw.feature_mode ?? DEFAULT_ML_PARAMS.feature_mode),
    macro_series_ids: Array.isArray(macroIds)
      ? macroIds.map(String)
      : DEFAULT_ML_PARAMS.macro_series_ids,
    macro_publication_lag_days:
      (raw.macro_publication_lag_days as Record<string, number> | undefined) ??
      DEFAULT_ML_PARAMS.macro_publication_lag_days,
    fundamental_metrics: Array.isArray(fundamentalMetrics)
      ? fundamentalMetrics.map(String)
      : DEFAULT_ML_PARAMS.fundamental_metrics,
    fundamental_period_type:
      periodType === 'annual' || periodType === 'quarterly'
        ? periodType
        : DEFAULT_ML_PARAMS.fundamental_period_type,
    context_timeframes: Array.isArray(raw.context_timeframes)
      ? raw.context_timeframes.map(String)
      : DEFAULT_ML_PARAMS.context_timeframes,
    strategy_feature_ids: Array.isArray(raw.strategy_feature_ids)
      ? raw.strategy_feature_ids.map(String)
      : DEFAULT_ML_PARAMS.strategy_feature_ids,
    strategy_feature_params:
      (raw.strategy_feature_params as Record<string, Record<string, unknown>> | undefined) ??
      DEFAULT_ML_PARAMS.strategy_feature_params,
    label_mode:
      raw.label_mode === 'meta_label'
        ? 'meta_label'
        : raw.label_mode === 'ternary'
          ? 'ternary'
          : 'binary',
    label_threshold: Number(raw.label_threshold ?? DEFAULT_ML_PARAMS.label_threshold),
    label_method: raw.label_method === 'mean' ? 'mean' : 'endpoint',
    label_horizon: Number(raw.label_horizon ?? DEFAULT_ML_PARAMS.label_horizon),
    warmup_bars: resolveWarmupBars({
      warmup_bars: Number(raw.warmup_bars ?? DEFAULT_ML_PARAMS.warmup_bars),
    }),
    train_bars: Number(raw.train_bars ?? DEFAULT_ML_PARAMS.train_bars),
    test_bars: Number(raw.test_bars ?? DEFAULT_ML_PARAMS.test_bars),
    step_bars: Number(raw.step_bars ?? DEFAULT_ML_PARAMS.step_bars),
    buy_threshold: Number(raw.buy_threshold ?? DEFAULT_ML_PARAMS.buy_threshold),
    sell_threshold: Number(raw.sell_threshold ?? DEFAULT_ML_PARAMS.sell_threshold),
    inference_eval_scope:
      raw.inference_eval_scope === 'in_sample' ? 'in_sample' : 'holdout',
    include_news_sentiment: Boolean(raw.include_news_sentiment),
    random_forest_estimators: Number(
      raw.random_forest_estimators ?? DEFAULT_ML_PARAMS.random_forest_estimators,
    ),
    gradient_boosting_max_iter: Number(
      raw.gradient_boosting_max_iter ?? DEFAULT_ML_PARAMS.gradient_boosting_max_iter,
    ),
    knn_neighbors: Number(raw.knn_neighbors ?? DEFAULT_ML_PARAMS.knn_neighbors),
    xgboost_estimators: Number(raw.xgboost_estimators ?? DEFAULT_ML_PARAMS.xgboost_estimators),
    xgboost_max_depth: Number(raw.xgboost_max_depth ?? DEFAULT_ML_PARAMS.xgboost_max_depth),
    xgboost_learning_rate: Number(
      raw.xgboost_learning_rate ?? DEFAULT_ML_PARAMS.xgboost_learning_rate,
    ),
    min_class_probability: raw.min_class_probability != null
      ? Number(raw.min_class_probability)
      : undefined,
    slippage_bps: Number(raw.slippage_bps ?? DEFAULT_ML_PARAMS.slippage_bps ?? 0),
    base_strategy_id: raw.base_strategy_id != null ? String(raw.base_strategy_id) : undefined,
    base_strategy_params:
      (raw.base_strategy_params as Record<string, unknown> | undefined) ??
      undefined,
    exit_policy:
      raw.exit_policy === 'signal_only' ||
      raw.exit_policy === 'label_horizon' ||
      raw.exit_policy === 'atr_bracket' ||
      raw.exit_policy === 'combined'
        ? raw.exit_policy
        : undefined,
    max_hold_bars: raw.max_hold_bars != null ? Number(raw.max_hold_bars) : undefined,
    atr_period: raw.atr_period != null ? Number(raw.atr_period) : DEFAULT_ML_PARAMS.atr_period,
    profit_atr_mult:
      raw.profit_atr_mult != null
        ? Number(raw.profit_atr_mult)
        : DEFAULT_ML_PARAMS.profit_atr_mult,
    stop_atr_mult:
      raw.stop_atr_mult != null ? Number(raw.stop_atr_mult) : DEFAULT_ML_PARAMS.stop_atr_mult,
    max_horizon_bars:
      raw.max_horizon_bars != null
        ? Number(raw.max_horizon_bars)
        : DEFAULT_ML_PARAMS.max_horizon_bars,
    meta_gate_threshold:
      raw.meta_gate_threshold != null
        ? Number(raw.meta_gate_threshold)
        : DEFAULT_ML_PARAMS.meta_gate_threshold,
    denoise_method:
      raw.denoise_method === 'kalman' || raw.denoise_method === 'wavelet'
        ? raw.denoise_method
        : DEFAULT_ML_PARAMS.denoise_method,
    include_cross_sectional_factors: Boolean(
      raw.include_cross_sectional_factors ?? DEFAULT_ML_PARAMS.include_cross_sectional_factors,
    ),
    include_metadata_features: Boolean(
      raw.include_metadata_features ?? DEFAULT_ML_PARAMS.include_metadata_features,
    ),
    dynamic_indicator_selection: Boolean(
      raw.dynamic_indicator_selection ?? DEFAULT_ML_PARAMS.dynamic_indicator_selection,
    ),
    indicator_groups: parseIndicatorGroupsFromRaw(raw.indicator_groups),
    correlation_prune_threshold: Number(
      raw.correlation_prune_threshold ?? DEFAULT_ML_PARAMS.correlation_prune_threshold,
    ),
    sizing_method:
      raw.sizing_method === 'kelly' || raw.sizing_method === 'hrp'
        ? raw.sizing_method
        : DEFAULT_ML_PARAMS.sizing_method,
    kelly_fraction: Number(raw.kelly_fraction ?? DEFAULT_ML_PARAMS.kelly_fraction),
    hrp_lookback_bars: Number(raw.hrp_lookback_bars ?? DEFAULT_ML_PARAMS.hrp_lookback_bars),
    rebalance_frequency: Number(
      raw.rebalance_frequency ?? DEFAULT_ML_PARAMS.rebalance_frequency,
    ),
    hrp_linkage_method:
      raw.hrp_linkage_method === 'ward' ? 'ward' : DEFAULT_ML_PARAMS.hrp_linkage_method,
    lstm_seq_length: Number(raw.lstm_seq_length ?? DEFAULT_ML_PARAMS.lstm_seq_length),
    lstm_hidden_size: Number(raw.lstm_hidden_size ?? DEFAULT_ML_PARAMS.lstm_hidden_size),
    lstm_num_layers: Number(raw.lstm_num_layers ?? DEFAULT_ML_PARAMS.lstm_num_layers),
    lstm_epochs: Number(raw.lstm_epochs ?? DEFAULT_ML_PARAMS.lstm_epochs),
    lstm_dropout: Number(raw.lstm_dropout ?? DEFAULT_ML_PARAMS.lstm_dropout),
    lstm_learning_rate: Number(
      raw.lstm_learning_rate ?? DEFAULT_ML_PARAMS.lstm_learning_rate,
    ),
    lstm_batch_size: Number(raw.lstm_batch_size ?? DEFAULT_ML_PARAMS.lstm_batch_size),
    technical_pca_enabled: Boolean(
      raw.technical_pca_enabled ?? DEFAULT_ML_PARAMS.technical_pca_enabled,
    ),
    technical_pca_variance_threshold: Number(
      raw.technical_pca_variance_threshold ?? DEFAULT_ML_PARAMS.technical_pca_variance_threshold,
    ),
    macro_features_mode:
      raw.macro_features_mode === 'changes_only' ? 'changes_only' : 'full',
    macro_pca_enabled: Boolean(
      raw.macro_pca_enabled ?? DEFAULT_ML_PARAMS.macro_pca_enabled,
    ),
    macro_pca_variance_threshold: Number(
      raw.macro_pca_variance_threshold ?? DEFAULT_ML_PARAMS.macro_pca_variance_threshold,
    ),
    macro_pca_input_mode:
      raw.macro_pca_input_mode === 'all_macro' ? 'all_macro' : 'changes_only',
    fundamental_features_mode:
      raw.fundamental_features_mode === 'growth_only' ? 'growth_only' : 'full',
    fundamental_pca_enabled: Boolean(
      raw.fundamental_pca_enabled ?? DEFAULT_ML_PARAMS.fundamental_pca_enabled,
    ),
    fundamental_pca_variance_threshold: Number(
      raw.fundamental_pca_variance_threshold
        ?? DEFAULT_ML_PARAMS.fundamental_pca_variance_threshold,
    ),
    fundamental_pca_input_mode:
      raw.fundamental_pca_input_mode === 'all_fundamental'
        ? 'all_fundamental'
        : raw.fundamental_pca_input_mode === 'growth_only'
          ? 'growth_only'
          : 'kpi_only',
  };
}

export function minimumBarsRequired(
  params: Pick<MlParams, WalkForwardParamKey | 'warmup_bars'> & {
    label_mode?: MlParams['label_mode'];
    max_horizon_bars?: number;
  },
): number {
  const horizon =
    params.label_mode === 'meta_label'
      ? Number(params.max_horizon_bars ?? 48)
      : params.label_horizon;
  return resolveWarmupBars(params) + params.train_bars + params.test_bars + horizon;
}

export function estimateWalkForwardFoldCount(
  barCount: number,
  trainBars: number,
  testBars: number,
  stepBars: number,
): number {
  if (barCount < trainBars + testBars || trainBars < 1 || testBars < 1 || stepBars < 1) {
    return 0;
  }

  let folds = 0;
  let trainStart = 0;
  while (trainStart + trainBars + testBars <= barCount) {
    folds += 1;
    trainStart += stepBars;
  }
  return folds;
}

export function validateWalkForwardParams(
  params: WalkForwardParams,
  barCount?: number | null,
): string | null {
  for (const key of WALK_FORWARD_PARAM_KEYS) {
    const value = params[key];
    const { min, max } = WALK_FORWARD_CONSTRAINTS[key];
    if (!Number.isFinite(value)) {
      return `${key.replace(/_/g, ' ')} must be a number.`;
    }
    if (value < min || value > max) {
      return `${key.replace(/_/g, ' ')} must be between ${min} and ${max}.`;
    }
  }

  const warmup = resolveWarmupBars(params);
  if (params.train_bars <= warmup) {
    return `Train bars must be greater than warmup bars (${warmup}).`;
  }

  if (minimumBarsRequired(params) < warmup + 2) {
    return 'Walk-forward windows require more bars.';
  }

  if (barCount != null && barCount > 0 && minimumBarsRequired(params) > barCount) {
    const required = minimumBarsRequired(params);
    const maxTrain = barCount - warmup - params.test_bars - params.label_horizon;
    return (
      `Date range has ~${barCount} bars but ${required} are required (includes feature warmup). ` +
      `Max train bars at current test/horizon: ${Math.max(WALK_FORWARD_CONSTRAINTS.train_bars.min, maxTrain)}.`
    );
  }

  if (barCount != null && barCount > 0) {
    const folds = estimateWalkForwardFoldCount(
      barCount,
      params.train_bars,
      params.test_bars,
      params.step_bars,
    );
    if (folds === 0) {
      return 'Walk-forward settings cannot produce any folds for the selected date range.';
    }
  }

  return null;
}

export function validateMetaGateThreshold(threshold: number): string | null {
  if (threshold < 0.51 || threshold > 0.99) {
    return 'Meta gate threshold must be between 0.51 and 0.99.';
  }
  return null;
}

export function validateMlParams(
  params: MlParams,
  model?: MlModelCatalogItem,
): string | null {
  const labelMode = params.label_mode ?? 'binary';
  if (labelMode === 'meta_label') {
    const gateError = validateMetaGateThreshold(
      params.meta_gate_threshold ?? DEFAULT_ML_PARAMS.meta_gate_threshold ?? 0.65,
    );
    if (gateError) {
      return gateError;
    }
  } else if (params.buy_threshold <= params.sell_threshold) {
    return 'Buy threshold must be greater than sell threshold.';
  }

  if (model) {
    for (const [key, constraint] of Object.entries(model.constraints)) {
      const value = params[key as keyof MlParams];
      if (typeof value !== 'number') continue;
      if (value < constraint.min || value > constraint.max) {
        return `${key.replace(/_/g, ' ')} must be between ${constraint.min} and ${constraint.max}.`;
      }
    }
  }

  const warmup = resolveWarmupBars(params);
  if (params.train_bars <= warmup) {
    return `Train bars must be greater than warmup bars (${warmup}).`;
  }

  if (minimumBarsRequired(params) < warmup + 2) {
    return 'Walk-forward windows require more bars.';
  }

  const indicatorError = validateIndicatorGroups(params);
  if (indicatorError) {
    return indicatorError;
  }

  if (featureModeUsesMacro(params.feature_mode)) {
    if (!params.macro_series_ids?.length) {
      return 'Select at least one macro series for prices + macro mode.';
    }
  }

  if (params.feature_mode === 'prices_macro_fundamentals') {
    if (!params.fundamental_metrics?.length) {
      return 'Select at least one fundamental metric for full feature mode.';
    }
  }

  return null;
}

export function macroCoverageWarning(
  selectedIds: string[],
  ingestedIds: Set<string>,
): string | null {
  const missing = selectedIds.filter((id) => !ingestedIds.has(id));
  if (missing.length === 0) {
    return null;
  }
  return `Selected macro series not ingested: ${missing.join(', ')}. They will be omitted at run time.`;
}

export function fundamentalEntitlementWarning(
  symbol: string,
  entitled: boolean,
): string | null {
  if (entitled) {
    return null;
  }
  return `${symbol.toUpperCase()} is not entitled for Tiingo fundamentals on the current tier. Full mode requires an entitled symbol.`;
}

export function isFundamentalsEntitled(
  symbol: string,
  entitlement: Record<string, unknown> | null | undefined,
): boolean {
  if (!entitlement) {
    return true;
  }
  if (Boolean(entitlement.addon_active)) {
    return true;
  }
  const dow30 = entitlement.dow30_symbols;
  if (!Array.isArray(dow30)) {
    return false;
  }
  return dow30.map(String).includes(symbol.toUpperCase());
}

export function fundamentalCoverageWarning(
  symbol: string,
  hasCoverage: boolean,
): string | null {
  if (hasCoverage) {
    return null;
  }
  return `No ingested fundamentals found for ${symbol.toUpperCase()}. Ingest fundamentals before running full mode.`;
}

export function fundamentalMetricCoverageWarning(
  selectedMetrics: string[],
  availableMetrics: Set<string>,
): string | null {
  const missing = selectedMetrics.filter((code) => !availableMetrics.has(code));
  if (missing.length === 0) {
    return null;
  }
  return `Selected fundamental metrics not ingested for this symbol: ${missing.join(', ')}. They will be omitted at run time.`;
}

export function isRandomForestModel(modelType: string): boolean {
  return modelType === 'ml_random_forest';
}

export function isGradientBoostingModel(modelType: string): boolean {
  return modelType === 'ml_gradient_boosting';
}

export function isXgboostModel(modelType: string): boolean {
  return modelType === 'ml_xgboost';
}

export function isKnnModel(modelType: string): boolean {
  return modelType === 'ml_knn';
}

export function isTreeModel(modelType: string): boolean {
  return (
    isRandomForestModel(modelType) ||
    isGradientBoostingModel(modelType) ||
    isXgboostModel(modelType)
  );
}

export function supportsFeatureImportance(modelType: string): boolean {
  return isTreeModel(modelType);
}

export const ML_COMPARE_FEATURE_MODES = ML_FEATURE_MODES.map((mode) => ({
  value: mode.value,
  label: mode.label,
}));

export function formatMetricPercent(value?: number | null): string {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }
  return `${(value * 100).toFixed(1)}%`;
}

export function formatOosAccuracy(value?: number | null): string {
  return formatMetricPercent(value);
}

const HYPERPARAM_FIELD_LABELS: Record<string, string> = {
  random_forest_estimators: ML_FIELD_LABELS.random_forest_estimators,
  gradient_boosting_max_iter: ML_FIELD_LABELS.gradient_boosting_max_iter,
  knn_neighbors: 'KNN neighbors',
  xgboost_max_depth: 'XGBoost max depth',
  xgboost_learning_rate: 'XGBoost learning rate',
};

function formatAppliedHyperparams(bestParams: Record<string, unknown>): string {
  const entries = Object.entries(bestParams);
  if (entries.length === 0) {
    return '';
  }
  return entries
    .map(([key, value]) => {
      const label = HYPERPARAM_FIELD_LABELS[key] ?? key.replace(/_/g, ' ');
      return `${label} = ${String(value)}`;
    })
    .join(', ');
}

export function formatHyperparameterSearchMessage(
  response: MlHyperparameterSearchResponse,
  modelLabel?: string,
): string {
  if (response.tuned === false) {
    const name = modelLabel ?? 'This model';
    return `No hyperparameters to tune for ${name}. Your current settings were kept.`;
  }
  if (response.tuned && response.best_score != null) {
    const score = `Best CV F1 macro: ${formatMetricPercent(response.best_score)}`;
    const applied = formatAppliedHyperparams(response.best_params);
    if (applied) {
      return `${score}. Applied: ${applied}.`;
    }
    return `Hyperparameter search completed. ${score}.`;
  }
  return 'Hyperparameter search completed.';
}
