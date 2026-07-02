import { describe, expect, it } from 'vitest';
import { validateMlParams } from '../utils/mlBacktestConfig';
import {
  NOISE_REDUCTION_ML_DEFAULTS,
  applyNoiseReductionDefaults,
  buildSimplifiedMlParams,
  mergePrimaryMlChoices,
} from '../utils/mlNoiseReductionPreset';

describe('mlNoiseReductionPreset', () => {
  it('enables PCA flags and keeps all indicator groups off dynamic selection', () => {
    const params = applyNoiseReductionDefaults({
      feature_mode: 'prices_macro',
      dynamic_indicator_selection: true,
      technical_pca_enabled: false,
      macro_pca_enabled: false,
      fundamental_pca_enabled: false,
      train_bars: 252,
      test_bars: 63,
      step_bars: 63,
      label_horizon: 5,
      buy_threshold: 0.55,
      sell_threshold: 0.45,
    });

    expect(params.technical_pca_enabled).toBe(true);
    expect(params.macro_pca_enabled).toBe(true);
    expect(params.fundamental_pca_enabled).toBe(true);
    expect(params.dynamic_indicator_selection).toBe(false);
    expect(params.macro_features_mode).toBe('changes_only');
    expect(params.fundamental_features_mode).toBe('growth_only');
    expect(params.correlation_prune_threshold).toBe(0.75);
  });

  it('buildSimplifiedMlParams produces valid ml params', () => {
    const params = buildSimplifiedMlParams({
      featureMode: 'prices_macro_fundamentals',
      includeNewsSentiment: true,
      modelType: 'ml_gradient_boosting',
      labelMode: 'binary',
      timeframe: '1d',
      assetType: 'equity',
    });

    expect(params.feature_mode).toBe('prices_macro_fundamentals');
    expect(params.include_news_sentiment).toBe(true);
    expect(params.macro_series_ids?.length).toBeGreaterThan(0);
    expect(params.fundamental_metrics?.length).toBeGreaterThan(0);
    expect(validateMlParams(params)).toBeNull();
  });

  it('mergePrimaryMlChoices preserves expert macro series when set', () => {
    const merged = mergePrimaryMlChoices(
      {
        ...buildSimplifiedMlParams({
          featureMode: 'prices_macro',
          includeNewsSentiment: false,
          modelType: 'ml_logistic',
          labelMode: 'binary',
          timeframe: '1d',
        }),
        macro_series_ids: ['DFF'],
      },
      { featureMode: 'prices_macro', assetType: 'equity', timeframe: '1d' },
      'equity',
    );

    expect(merged.macro_series_ids).toEqual(['DFF']);
    expect(merged.technical_pca_enabled).toBe(true);
  });

  it('exports stable noise reduction defaults', () => {
    expect(NOISE_REDUCTION_ML_DEFAULTS.denoise_method).toBe('none');
    expect(NOISE_REDUCTION_ML_DEFAULTS.macro_pca_input_mode).toBe('changes_only');
  });
});
