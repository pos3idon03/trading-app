import { describe, expect, it } from 'vitest';
import {
  applyAlignedExitPolicy,
  defaultExitPolicyForLabelMode,
} from '../utils/mlBacktestConfig';

describe('mlExitPolicy', () => {
  it('defaultExitPolicyForLabelMode maps binary and meta_label', () => {
    expect(defaultExitPolicyForLabelMode('binary')).toBe('label_horizon');
    expect(defaultExitPolicyForLabelMode('meta_label')).toBe('atr_bracket');
  });

  it('applyAlignedExitPolicy sets horizon-aligned fields', () => {
    const next = applyAlignedExitPolicy({
      feature_mode: 'prices_only',
      label_mode: 'binary',
      label_horizon: 7,
      train_bars: 100,
      test_bars: 30,
      step_bars: 30,
      buy_threshold: 0.55,
      sell_threshold: 0.45,
    });
    expect(next.exit_policy).toBe('label_horizon');
    expect(next.max_hold_bars).toBe(7);
  });
});
