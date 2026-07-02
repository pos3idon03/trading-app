import { describe, expect, it } from 'vitest';
import {
  computeWalkForwardBudget,
  formatMlDateRangeLabel,
  isUsingMaxPreset,
  maxWalkForwardParamValue,
} from '../utils/mlUniverseBudget';

const params = {
  warmup_bars: 50,
  train_bars: 150,
  test_bars: 52,
  step_bars: 52,
  label_horizon: 3,
};

describe('mlUniverseBudget', () => {
  it('computeWalkForwardBudget breaks down bar usage', () => {
    const budget = computeWalkForwardBudget(1612, params);
    expect(budget.warmupBars).toBe(50);
    expect(budget.labelTail).toBe(3);
    expect(budget.minimumRequired).toBe(50 + 150 + 52 + 3);
    expect(budget.walkForwardBudget).toBe(1612 - 50 - 3);
    expect(budget.remainingBars).toBe(1612 - budget.minimumRequired);
    expect(budget.simulationStartBarIndex).toBe(150);
    expect(budget.structuralFolds).toBeGreaterThan(0);
  });

  it('maxWalkForwardParamValue respects fixed siblings', () => {
    expect(maxWalkForwardParamValue('train_bars', 1612, params)).toBe(1612 - 50 - 52 - 3);
    expect(maxWalkForwardParamValue('test_bars', 1612, params)).toBe(500);
    expect(maxWalkForwardParamValue('label_horizon', 1612, params)).toBe(60);
    expect(maxWalkForwardParamValue('step_bars', 1612, params)).toBe(500);
  });

  it('maxWalkForwardParamValue clamps to static constraints', () => {
    expect(maxWalkForwardParamValue('train_bars', 100, params)).toBe(10);
  });

  it('formatMlDateRangeLabel prefers actual bar timestamps', () => {
    expect(
      formatMlDateRangeLabel(
        { preset: 'MAX', start: '2020-01-01', end: '2026-05-25' },
        '2020-01-02T00:00:00Z',
        '2026-05-23T00:00:00Z',
      ),
    ).toBe('2020-01-02 → 2026-05-23');
  });

  it('formatMlDateRangeLabel labels MAX preset', () => {
    expect(formatMlDateRangeLabel({ preset: 'MAX' })).toBe('MAX (full ingested history)');
  });

  it('isUsingMaxPreset detects unset custom range', () => {
    expect(isUsingMaxPreset({ preset: 'MAX' })).toBe(true);
    expect(isUsingMaxPreset({ preset: 'MAX', start: '2020-01-01' })).toBe(false);
  });
});
