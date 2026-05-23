import { describe, expect, it } from 'vitest';
import {
  buildOosAccuracyChartData,
  confusionMatrixMaxValue,
  filterRecordsFromSimulationStart,
  formatSimulationPeriodLabel,
  topFeatureImportance,
} from '../utils/mlBacktestEvaluation';

describe('mlBacktestEvaluation', () => {
  it('returns top feature importance items in order', () => {
    const items = [
      { name: 'a', value: 0.1 },
      { name: 'b', value: 0.5 },
      { name: 'c', value: 0.3 },
    ];
    expect(topFeatureImportance(items, 2)).toEqual([
      { name: 'b', value: 0.5 },
      { name: 'c', value: 0.3 },
    ]);
  });

  it('builds OOS accuracy chart rows with fold index', () => {
    const data = buildOosAccuracyChartData([0.5, 0.6]);
    expect(data).toEqual([
      { window: 1, accuracy: 0.5, accuracyPct: 50 },
      { window: 2, accuracy: 0.6, accuracyPct: 60 },
    ]);
  });

  it('computes confusion matrix max for color scaling', () => {
    expect(confusionMatrixMaxValue([[1, 2], [3, 4]])).toBe(4);
    expect(confusionMatrixMaxValue(undefined)).toBe(1);
  });

  it('filters OHLCV records from simulation start date', () => {
    const records = [
      { time: '2020-01-01T00:00:00Z', open: 1, high: 1, low: 1, close: 1, volume: 1, source: 'x' },
      { time: '2020-06-01T00:00:00Z', open: 2, high: 2, low: 2, close: 2, volume: 2, source: 'x' },
    ];
    const filtered = filterRecordsFromSimulationStart(records, '2020-05-01');
    expect(filtered).toHaveLength(1);
    expect(filtered[0].time).toContain('2020-06-01');
  });

  it('returns all records when simulation start is missing', () => {
    const records = [{ time: '2020-01-01T00:00:00Z' }];
    expect(filterRecordsFromSimulationStart(records, null)).toEqual(records);
  });

  it('formats simulation period label', () => {
    expect(formatSimulationPeriodLabel('2020-05-01T00:00:00Z', '2021-01-01')).toBe(
      '2020-05-01 – 2021-01-01',
    );
    expect(formatSimulationPeriodLabel(null, '2021-01-01')).toBeNull();
  });
});
