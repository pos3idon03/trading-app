import type { MlHyperparameterSearchResponse, MlModelCatalogItem, MlParams } from '../api/mlBacktestTypes';
import { FUNDAMENTAL_METRIC_CODES } from '../constants/fundamentalsMetrics';
import { INTRADAY_BAR_LIMIT, INTRADAY_TIMEFRAMES } from '../constants/timeframes';
import { ML_FIELD_LABELS } from './mlBacktestHelp';

export const FEATURE_WARMUP_BARS = 50;

const TRADING_MINUTES_PER_DAY = 6.5 * 60;
const MIN_TRAIN_BARS = 30;
const MIN_TEST_BARS = 5;

export function barsPerYear(timeframe: string): number {
  if (timeframe === '1d') return 252;
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
  return 252 * (TRADING_MINUTES_PER_DAY / bucket);
}

export function defaultWalkForwardParams(timeframe: string): Pick<
  MlParams,
  'train_bars' | 'test_bars' | 'step_bars' | 'label_horizon'
> {
  const bpy = barsPerYear(timeframe);
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
): Pick<MlParams, 'train_bars' | 'test_bars' | 'step_bars' | 'label_horizon'> {
  const ideal = defaultWalkForwardParams(timeframe);
  if (barCount == null || barCount <= 0) {
    return ideal;
  }
  return fitWalkForwardParamsToBarCount(barCount, timeframe);
}

export const DEFAULT_MACRO_SERIES_IDS = ['DFF', 'DGS2', 'DGS10', 'T10Y2Y', 'CPIAUCSL', 'CPILFESL', 'PCEPI'];

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
  train_bars: 252,
  test_bars: 63,
  step_bars: 63,
  buy_threshold: 0.55,
  sell_threshold: 0.45,
  random_forest_estimators: 100,
  gradient_boosting_max_iter: 100,
  knn_neighbors: 5,
  xgboost_estimators: 100,
  xgboost_max_depth: 6,
  xgboost_learning_rate: 0.1,
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
    label_mode: raw.label_mode === 'ternary' ? 'ternary' : 'binary',
    label_threshold: Number(raw.label_threshold ?? DEFAULT_ML_PARAMS.label_threshold),
    label_method: raw.label_method === 'mean' ? 'mean' : 'endpoint',
    label_horizon: Number(raw.label_horizon ?? DEFAULT_ML_PARAMS.label_horizon),
    train_bars: Number(raw.train_bars ?? DEFAULT_ML_PARAMS.train_bars),
    test_bars: Number(raw.test_bars ?? DEFAULT_ML_PARAMS.test_bars),
    step_bars: Number(raw.step_bars ?? DEFAULT_ML_PARAMS.step_bars),
    buy_threshold: Number(raw.buy_threshold ?? DEFAULT_ML_PARAMS.buy_threshold),
    sell_threshold: Number(raw.sell_threshold ?? DEFAULT_ML_PARAMS.sell_threshold),
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
  };
}

export function minimumBarsRequired(params: MlParams): number {
  return FEATURE_WARMUP_BARS + params.train_bars + params.test_bars + params.label_horizon;
}

export function validateMlParams(
  params: MlParams,
  model?: MlModelCatalogItem,
): string | null {
  if (params.buy_threshold <= params.sell_threshold) {
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

  if (minimumBarsRequired(params) < FEATURE_WARMUP_BARS + 2) {
    return 'Walk-forward windows require more bars.';
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
