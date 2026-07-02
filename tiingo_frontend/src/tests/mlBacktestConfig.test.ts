import { describe, expect, it } from 'vitest';
import {
  DEFAULT_ML_PARAMS,
  FEATURE_WARMUP_BARS,
  barsPerYear,
  getCryptoMlPreset,
  defaultWalkForwardParams,
  fitWalkForwardParamsToBarCount,
  formatOosAccuracy,
  formatHyperparameterSearchMessage,
  featureModeUsesMacro,
  isGradientBoostingModel,
  isRandomForestModel,
  isTreeModel,
  ML_COMPARE_FEATURE_MODES,
  macroCoverageWarning,
  fundamentalCoverageWarning,
  fundamentalMetricCoverageWarning,
  isFundamentalsEntitled,
  minimumBarsRequired,
  parseMlParams,
  validateMlParams,
  validateWalkForwardParams,
  estimateWalkForwardFoldCount,
} from '../utils/mlBacktestConfig';

describe('mlBacktestConfig', () => {
  it('parses default params', () => {
    const params = parseMlParams({});
    expect(DEFAULT_ML_PARAMS.correlation_prune_threshold).toBe(0.75);
    expect(DEFAULT_ML_PARAMS.technical_pca_enabled).toBe(true);
    expect(DEFAULT_ML_PARAMS.macro_pca_enabled).toBe(true);
    expect(params.feature_mode).toBe('prices_only');
    expect(params.train_bars).toBe(252);
    expect(params.label_horizon).toBe(5);
    expect(params.include_news_sentiment).toBe(false);
  });

  it('parses include_news_sentiment flag', () => {
    const params = parseMlParams({ include_news_sentiment: true });
    expect(params.include_news_sentiment).toBe(true);
  });

  it('crypto preset uses meta_label and 24/7 hourly walk-forward', () => {
    const preset = getCryptoMlPreset('1h');
    expect(preset.label_mode).toBe('meta_label');
    expect(preset.feature_mode).toBe('prices_macro');
    expect(preset.include_news_sentiment).toBe(true);
    expect(preset.train_bars).toBeGreaterThan(1000);
    expect(barsPerYear('1h', 'crypto')).toBeGreaterThan(barsPerYear('1h', 'equity'));
  });

  it('computes minimum bars including warmup and label horizon', () => {
    const params = { ...DEFAULT_ML_PARAMS, train_bars: 100, test_bars: 20, label_horizon: 5 };
    expect(minimumBarsRequired(params)).toBe(FEATURE_WARMUP_BARS + 100 + 20 + 5);
  });

  it('computes minimum bars with custom warmup', () => {
    const params = { ...DEFAULT_ML_PARAMS, warmup_bars: 100, train_bars: 120, test_bars: 20, label_horizon: 5 };
    expect(minimumBarsRequired(params)).toBe(100 + 120 + 20 + 5);
  });

  it('rejects train bars at or below warmup', () => {
    const params = { ...DEFAULT_ML_PARAMS, warmup_bars: 300, train_bars: 252 };
    expect(validateWalkForwardParams(params)).toMatch(/warmup/i);
  });

  it('rejects buy threshold below sell threshold', () => {
    const params = { ...DEFAULT_ML_PARAMS, buy_threshold: 0.4, sell_threshold: 0.6 };
    expect(validateMlParams(params)).toMatch(/Buy threshold/);
  });

  it('validates meta gate threshold for meta-label mode', () => {
    const params = {
      ...DEFAULT_ML_PARAMS,
      label_mode: 'meta_label' as const,
      meta_gate_threshold: 0.4,
    };
    expect(validateMlParams(params)).toMatch(/Meta gate/i);
  });

  it('skips buy/sell ordering check for meta-label mode', () => {
    const params = {
      ...DEFAULT_ML_PARAMS,
      label_mode: 'meta_label' as const,
      buy_threshold: 0.4,
      sell_threshold: 0.6,
      meta_gate_threshold: 0.65,
    };
    expect(validateMlParams(params)).toBeNull();
  });

  it('validates against model constraints', () => {
    const error = validateMlParams(
      { ...DEFAULT_ML_PARAMS, train_bars: 9 },
      {
        id: 'ml_logistic',
        label: 'Logistic',
        description: '',
        params: DEFAULT_ML_PARAMS,
        constraints: { train_bars: { min: 10, max: 2000 } },
      },
    );
    expect(error).toMatch(/train bars/i);
  });

  it('validateWalkForwardParams accepts viable params above warmup', () => {
    const params = {
      warmup_bars: 50,
      train_bars: 100,
      test_bars: 20,
      step_bars: 20,
      label_horizon: 2,
    };
    expect(validateWalkForwardParams(params, 250)).toBeNull();
  });

  it('validateWalkForwardParams rejects train_bars below minimum', () => {
    const params = {
      train_bars: 9,
      test_bars: 20,
      step_bars: 20,
      label_horizon: 2,
    };
    expect(validateWalkForwardParams(params)).toMatch(/train bars/i);
  });

  it('validateWalkForwardParams includes max train hint when range is too short', () => {
    const params = {
      warmup_bars: 50,
      train_bars: 150,
      test_bars: 52,
      step_bars: 52,
      label_horizon: 3,
    };
    expect(validateWalkForwardParams(params, 200)).toMatch(/Max train bars/);
  });

  it('estimateWalkForwardFoldCount counts sliding windows', () => {
    expect(estimateWalkForwardFoldCount(200, 60, 40, 40)).toBe(3);
    expect(estimateWalkForwardFoldCount(80, 60, 40, 40)).toBe(0);
  });

  it('detects random forest model type', () => {
    expect(isRandomForestModel('ml_random_forest')).toBe(true);
    expect(isRandomForestModel('ml_logistic')).toBe(false);
  });

  it('detects tree models for feature importance', () => {
    expect(isTreeModel('ml_random_forest')).toBe(true);
    expect(isTreeModel('ml_gradient_boosting')).toBe(true);
    expect(isTreeModel('ml_logistic')).toBe(false);
    expect(isGradientBoostingModel('ml_gradient_boosting')).toBe(true);
  });

  it('exposes compare presets for all feature modes', () => {
    expect(ML_COMPARE_FEATURE_MODES).toHaveLength(3);
    expect(ML_COMPARE_FEATURE_MODES.map((item) => item.value)).toContain('prices_only');
  });

  it('formats OOS accuracy as percentage', () => {
    expect(formatOosAccuracy(0.5123)).toBe('51.2%');
    expect(formatOosAccuracy(null)).toBe('—');
  });

  it('formats hyperparameter search message when model is not tunable', () => {
    expect(
      formatHyperparameterSearchMessage(
        { best_params: {}, best_score: null, tuned: false },
        'Logistic Regression',
      ),
    ).toBe(
      'No hyperparameters to tune for Logistic Regression. Your current settings were kept.',
    );
  });

  it('formats hyperparameter search message with score and applied params', () => {
    expect(
      formatHyperparameterSearchMessage({
        tuned: true,
        best_score: 0.523,
        best_params: { gradient_boosting_max_iter: 100 },
      }),
    ).toBe('Best CV F1 macro: 52.3%. Applied: Gradient boosting iterations = 100.');
  });

  it('formats hyperparameter search fallback message', () => {
    expect(
      formatHyperparameterSearchMessage({
        tuned: true,
        best_score: null,
        best_params: {},
      }),
    ).toBe('Hyperparameter search completed.');
  });

  it('scales walk-forward defaults for intraday timeframes', () => {
    const daily = defaultWalkForwardParams('1d');
    const hourly = defaultWalkForwardParams('1h');
    expect(hourly.train_bars).toBeGreaterThan(daily.train_bars);
    expect(hourly.test_bars).toBeGreaterThan(daily.test_bars);
  });

  it('fits walk-forward params to available bar count', () => {
    const fitted = fitWalkForwardParamsToBarCount(312, '5m');
    expect(minimumBarsRequired(fitted as typeof DEFAULT_ML_PARAMS)).toBeLessThanOrEqual(312);
    expect(fitted.train_bars).toBeLessThan(2000);
  });

  it('warns when selected macro series are not ingested', () => {
    const warning = macroCoverageWarning(['DFF', 'CPIAUCSL'], new Set(['DFF']));
    expect(warning).toMatch(/CPIAUCSL/);
  });

  it('identifies feature modes that use macro features', () => {
    expect(featureModeUsesMacro('prices_only')).toBe(false);
    expect(featureModeUsesMacro('prices_macro')).toBe(true);
    expect(featureModeUsesMacro('prices_macro_fundamentals')).toBe(true);
  });

  it('parses fundamental params for full feature mode', () => {
    const params = parseMlParams({
      feature_mode: 'prices_macro_fundamentals',
      fundamental_metrics: ['revenue', 'roe'],
      fundamental_period_type: 'annual',
    });
    expect(params.feature_mode).toBe('prices_macro_fundamentals');
    expect(params.fundamental_metrics).toEqual(['revenue', 'roe']);
    expect(params.fundamental_period_type).toBe('annual');
  });

  it('validates full feature mode requires fundamental metrics', () => {
    const params = {
      ...DEFAULT_ML_PARAMS,
      feature_mode: 'prices_macro_fundamentals',
      macro_series_ids: ['DFF'],
      fundamental_metrics: [],
    };
    expect(validateMlParams(params)).toMatch(/fundamental metric/i);
  });

  it('warns when symbol lacks fundamentals coverage', () => {
    expect(fundamentalCoverageWarning('XYZ', false)).toMatch(/XYZ/);
  });

  it('warns when selected fundamental metrics are missing', () => {
    const warning = fundamentalMetricCoverageWarning(['revenue', 'roe'], new Set(['revenue']));
    expect(warning).toMatch(/roe/);
  });

  it('detects fundamentals entitlement for dow30 symbols', () => {
    expect(
      isFundamentalsEntitled('AAPL', { addon_active: false, dow30_symbols: ['AAPL'] }),
    ).toBe(true);
    expect(
      isFundamentalsEntitled('XYZ', { addon_active: false, dow30_symbols: ['AAPL'] }),
    ).toBe(false);
    expect(isFundamentalsEntitled('XYZ', { addon_active: true, dow30_symbols: [] })).toBe(true);
  });
});
