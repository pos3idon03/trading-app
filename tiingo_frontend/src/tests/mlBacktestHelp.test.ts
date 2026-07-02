import { describe, expect, it } from 'vitest';
import {
  ML_FIELD_HELP,
  ML_FIELD_LABELS,
  ML_SUPPORTED_TIMEFRAMES,
  isMlTimeframeSupported,
  mlFieldHelp,
  mlFieldLabel,
} from '../utils/mlBacktestHelp';

const EXPECTED_KEYS = [
  'decision_timeframe',
  'model',
  'feature_mode',
  'macro_series_ids',
  'fundamental_metrics',
  'fundamental_period_type',
  'label_horizon',
  'train_bars',
  'test_bars',
  'step_bars',
  'buy_threshold',
  'sell_threshold',
  'random_forest_estimators',
  'gradient_boosting_max_iter',
  'run_mode',
  'saved_model',
  'initial_cash',
  'commission_bps',
  'include_news_sentiment',
  'label_mode',
  'meta_gate_threshold',
  'base_strategy_id',
  'slippage_bps',
  'correlation_prune_threshold',
] as const;

describe('mlBacktestHelp', () => {
  it('defines help text for all expected fields', () => {
    for (const key of EXPECTED_KEYS) {
      expect(ML_FIELD_HELP[key].length).toBeGreaterThan(10);
      expect(ML_FIELD_LABELS[key].length).toBeGreaterThan(0);
    }
  });

  it('exposes label and help accessors', () => {
    expect(mlFieldLabel('train_bars')).toBe('Train bars');
    expect(mlFieldHelp('train_bars')).toContain('walk-forward');
  });

  it('supports all OHLCV timeframes', () => {
    expect(ML_SUPPORTED_TIMEFRAMES.size).toBe(9);
    expect(isMlTimeframeSupported('1d')).toBe(true);
    expect(isMlTimeframeSupported('1h')).toBe(true);
    expect(isMlTimeframeSupported('1w')).toBe(true);
    expect(isMlTimeframeSupported('1mo')).toBe(true);
  });
});
