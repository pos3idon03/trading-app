import type { MlLabelMode, MlParams } from '../api/mlBacktestTypes';
import {
  CRYPTO_MACRO_SERIES_IDS,
  DEFAULT_FUNDAMENTAL_METRICS,
  DEFAULT_LABEL_MODE_BY_MODEL,
  DEFAULT_MACRO_SERIES_IDS,
  DEFAULT_ML_PARAMS,
  defaultWalkForwardParams,
} from './mlBacktestConfig';
import { DEFAULT_INDICATOR_GROUPS } from './mlIndicatorGroups';
import { defaultMetaLabelBaseStrategyId } from './mlStrategyFeatures';

export const NOISE_REDUCTION_ML_DEFAULTS: Partial<MlParams> = {
  dynamic_indicator_selection: false,
  indicator_groups: [...DEFAULT_INDICATOR_GROUPS],
  correlation_prune_threshold: 0.75,
  denoise_method: 'none',
  technical_pca_enabled: true,
  technical_pca_variance_threshold: 0.85,
  macro_features_mode: 'changes_only',
  macro_pca_enabled: true,
  macro_pca_input_mode: 'changes_only',
  macro_pca_variance_threshold: 0.85,
  fundamental_features_mode: 'growth_only',
  fundamental_pca_enabled: true,
  fundamental_pca_input_mode: 'kpi_only',
  fundamental_pca_variance_threshold: 0.85,
  macro_series_ids: [...DEFAULT_MACRO_SERIES_IDS],
  fundamental_metrics: [...DEFAULT_FUNDAMENTAL_METRICS],
};

export interface SimplifiedMlChoices {
  featureMode: string;
  includeNewsSentiment: boolean;
  modelType: string;
  labelMode: MlLabelMode;
  timeframe: string;
  assetType?: string;
  warmupBars?: number;
}

export function applyNoiseReductionDefaults(params: MlParams): MlParams {
  return {
    ...params,
    ...NOISE_REDUCTION_ML_DEFAULTS,
    macro_series_ids: params.macro_series_ids?.length
      ? params.macro_series_ids
      : [...(NOISE_REDUCTION_ML_DEFAULTS.macro_series_ids ?? DEFAULT_MACRO_SERIES_IDS)],
    fundamental_metrics: params.fundamental_metrics?.length
      ? params.fundamental_metrics
      : [...(NOISE_REDUCTION_ML_DEFAULTS.fundamental_metrics ?? DEFAULT_FUNDAMENTAL_METRICS)],
    indicator_groups: params.indicator_groups?.length
      ? params.indicator_groups
      : [...DEFAULT_INDICATOR_GROUPS],
  };
}

export function resolveMacroSeriesForAsset(assetType: string): string[] {
  return assetType === 'crypto' ? [...CRYPTO_MACRO_SERIES_IDS] : [...DEFAULT_MACRO_SERIES_IDS];
}

export function buildSimplifiedMlParams(choices: SimplifiedMlChoices): MlParams {
  const assetType = choices.assetType ?? 'equity';
  const labelMode =
    choices.labelMode ?? DEFAULT_LABEL_MODE_BY_MODEL[choices.modelType] ?? 'binary';
  const wfo = defaultWalkForwardParams(choices.timeframe, assetType);

  const base: MlParams = {
    ...DEFAULT_ML_PARAMS,
    ...wfo,
    feature_mode: choices.featureMode,
    include_news_sentiment: choices.includeNewsSentiment,
    label_mode: labelMode,
    warmup_bars: choices.warmupBars ?? DEFAULT_ML_PARAMS.warmup_bars,
    macro_series_ids: resolveMacroSeriesForAsset(assetType),
  };

  if (labelMode === 'meta_label') {
    base.base_strategy_id = defaultMetaLabelBaseStrategyId(assetType);
  }

  return applyNoiseReductionDefaults(base);
}

export function mergePrimaryMlChoices(
  current: MlParams,
  choices: Partial<SimplifiedMlChoices>,
  assetType: string = 'equity',
): MlParams {
  const featureMode = choices.featureMode ?? current.feature_mode;
  const includeNews =
    choices.includeNewsSentiment ?? Boolean(current.include_news_sentiment);
  const labelMode = choices.labelMode ?? current.label_mode ?? 'binary';
  const timeframe = choices.timeframe;

  let merged: MlParams = {
    ...current,
    feature_mode: featureMode,
    include_news_sentiment: includeNews,
    label_mode: labelMode,
  };

  if (timeframe) {
    merged = {
      ...merged,
      ...defaultWalkForwardParams(timeframe, assetType),
    };
  }

  if (labelMode === 'meta_label' && !merged.base_strategy_id) {
    merged.base_strategy_id = defaultMetaLabelBaseStrategyId(assetType);
  }

  return applyNoiseReductionDefaults(merged);
}
