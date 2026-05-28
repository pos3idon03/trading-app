import { describe, expect, it } from 'vitest';
import { buildMlWorkbookConfigSnapshot } from '../utils/mlWorkbookExport';

describe('buildMlWorkbookConfigSnapshot', () => {
  it('maps panel inputs to snake_case config snapshot', () => {
    const snapshot = buildMlWorkbookConfigSnapshot({
      initialCash: 10_000,
      commissionBps: 5,
      runMode: 'walk_forward',
      modelLabel: 'Logistic regression',
      appliedModelLabel: 'Applied label',
      dateRangeStart: '2020-01-01',
      dateRangeEnd: '2024-01-01',
    });

    expect(snapshot).toEqual({
      initial_cash: 10_000,
      commission_bps: 5,
      run_mode: 'walk_forward',
      model_label: 'Applied label',
      date_range_start: '2020-01-01',
      date_range_end: '2024-01-01',
    });
  });

  it('falls back to model label when applied label is missing', () => {
    const snapshot = buildMlWorkbookConfigSnapshot({
      initialCash: 10_000,
      commissionBps: 0,
      runMode: 'inference',
      modelLabel: 'Random forest',
    });

    expect(snapshot.model_label).toBe('Random forest');
  });
});
