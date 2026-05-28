import { describe, expect, it } from 'vitest';
import type { MlParams, MlWalkForwardReadiness } from '../api/mlBacktestTypes';
import {
  formatZeroOosGuidance,
  isReadinessReady,
  previewConfigFingerprint,
  readinessStatusTone,
} from '../utils/mlWalkForwardDiagnostics';
import { DEFAULT_ML_PARAMS } from '../utils/mlBacktestConfig';

const baseReadiness: MlWalkForwardReadiness = {
  total_bars: 300,
  warmup_bars: 50,
  valid_feature_rows: 200,
  labeled_rows: 240,
  trainable_rows: 180,
  structural_folds: 3,
  viable_folds: 2,
  train_bars: 120,
  test_bars: 60,
  step_bars: 60,
};

describe('mlWalkForwardDiagnostics', () => {
  it('builds a stable preview config fingerprint', () => {
    const params: MlParams = {
      ...DEFAULT_ML_PARAMS,
      context_timeframes: ['1h'],
      strategy_feature_ids: ['rsi'],
      train_bars: 120,
    };
    const first = previewConfigFingerprint(params);
    const second = previewConfigFingerprint({ ...params });
    expect(first).toBe(second);
    expect(first).toContain('"train_bars":120');
  });

  it('includes date range in preview config fingerprint', () => {
    const params: MlParams = { ...DEFAULT_ML_PARAMS };
    const withRange = previewConfigFingerprint(params, {
      preset: 'MAX',
      start: '2020-01-01',
      end: '2026-05-25',
    });
    const withoutRange = previewConfigFingerprint(params);
    expect(withRange).not.toBe(withoutRange);
    expect(withRange).toContain('"date_start":"2020-01-01"');
  });

  it('detects readiness from viable fold count', () => {
    expect(isReadinessReady(baseReadiness)).toBe(true);
    expect(isReadinessReady({ ...baseReadiness, viable_folds: 0 })).toBe(false);
    expect(isReadinessReady(undefined)).toBe(false);
  });

  it('maps readiness tone', () => {
    expect(readinessStatusTone(baseReadiness)).toBe('ready');
    expect(readinessStatusTone({ ...baseReadiness, viable_folds: 0 })).toBe('warning');
    expect(readinessStatusTone(undefined)).toBe('unknown');
  });

  it('guides zero OOS when features are missing', () => {
    const messages = formatZeroOosGuidance(
      { ...baseReadiness, valid_feature_rows: 0, viable_folds: 0 },
      { '0': 100, '1': 120 },
    );
    expect(messages[0]).toMatch(/No valid feature rows/);
  });

  it('guides zero OOS when folds cannot train', () => {
    const messages = formatZeroOosGuidance(
      { ...baseReadiness, viable_folds: 0 },
      { '0': 100, '1': 120 },
    );
    expect(messages[0]).toMatch(/Walk-forward cannot train/);
  });

  it('warns on one-sided label distribution', () => {
    const messages = formatZeroOosGuidance(baseReadiness, { '0': 950, '1': 50 });
    expect(messages.some((msg) => msg.includes('one-sided'))).toBe(true);
  });

  it('falls back when readiness is missing', () => {
    const messages = formatZeroOosGuidance(undefined, undefined);
    expect(messages[0]).toMatch(/Run data preview/);
  });
});
