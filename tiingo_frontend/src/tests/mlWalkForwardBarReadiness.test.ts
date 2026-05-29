import { describe, expect, it } from 'vitest';
import { FEATURE_WARMUP_BARS } from '../utils/mlBacktestConfig';
import {
  assessWalkForwardBarReadiness,
  cryptoBarReadinessTip,
  formatWalkForwardMinimumBreakdown,
} from '../utils/mlWalkForwardBarReadiness';

const params = {
  train_bars: 2000,
  test_bars: 500,
  step_bars: 500,
  label_horizon: 5,
};

const minimumForParams = FEATURE_WARMUP_BARS + 2000 + 500 + 5;

describe('mlWalkForwardBarReadiness', () => {
  it('reports loading state', () => {
    const result = assessWalkForwardBarReadiness(null, params, { loading: true });
    expect(result.status).toBe('loading');
    expect(result.availableBars).toBeNull();
  });

  it('reports insufficient bars with shortfall', () => {
    const result = assessWalkForwardBarReadiness(234, params);
    expect(result.status).toBe('insufficient_bars');
    expect(result.minimumRequired).toBe(minimumForParams);
    expect(result.shortfall).toBe(minimumForParams - 234);
  });

  it('reports ready when enough bars and folds exist', () => {
    const result = assessWalkForwardBarReadiness(3000, params);
    expect(result.status).toBe('ready');
    expect(result.structuralFolds).toBe(2);
    expect(result.headroom).toBe(3000 - minimumForParams);
  });

  it('formats minimum breakdown with warmup 200', () => {
    expect(
      formatWalkForwardMinimumBreakdown({
        warmup: FEATURE_WARMUP_BARS,
        train: 2000,
        test: 500,
        labelHorizon: 5,
      }),
    ).toContain(`${FEATURE_WARMUP_BARS} warmup + 2000 train + 500 test + 5 label tail`);
  });

  it('includes crypto hourly guidance for crypto 1h', () => {
    const result = assessWalkForwardBarReadiness(5000, params, {
      assetType: 'crypto',
      timeframe: '1h',
      labelMode: 'meta_label',
      maxHorizonBars: 48,
    });
    expect(result.cryptoTip).toContain('Crypto trains 24/7');
    expect(result.detail).toContain('Crypto trains 24/7');
  });

  it('meta_label requires more bars than binary for same train/test', () => {
    const binary = assessWalkForwardBarReadiness(3000, params, { labelMode: 'binary' });
    const meta = assessWalkForwardBarReadiness(3000, params, {
      labelMode: 'meta_label',
      maxHorizonBars: 48,
    });
    expect(meta.minimumRequired).toBeGreaterThan(binary.minimumRequired);
    expect(meta.breakdown.labelHorizon).toBe(48);
    expect(binary.breakdown.labelHorizon).toBe(5);
  });

  it('exposes crypto tip helper for daily timeframe', () => {
    expect(cryptoBarReadinessTip('crypto', '1d')).toContain('hourly');
  });
});
