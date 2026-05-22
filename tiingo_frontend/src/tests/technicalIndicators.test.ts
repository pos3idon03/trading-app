import { describe, expect, it } from 'vitest';
import {
  buildStandaloneChartData,
  computeEMA,
  computeRSI,
  computeSMA,
  trendSeriesKey,
} from '../utils/technicalIndicators';

describe('computeSMA', () => {
  it('returns null until period is reached', () => {
    expect(computeSMA([1, 2, 3, 4, 5], 3)).toEqual([null, null, 2, 3, 4]);
  });

  it('returns all null when period exceeds length', () => {
    expect(computeSMA([1, 2], 5)).toEqual([null, null]);
  });
});

describe('computeEMA', () => {
  it('returns null until period is reached', () => {
    const result = computeEMA([1, 2, 3, 4, 5], 3);
    expect(result.slice(0, 2)).toEqual([null, null]);
    expect(result[2]).toBeCloseTo(2, 5);
  });
});

describe('computeRSI', () => {
  it('returns null until period is satisfied', () => {
    const result = computeRSI([1, 2, 3, 4, 5, 6], 3);
    expect(result.slice(0, 3)).toEqual([null, null, null]);
    expect(result[3]).not.toBeNull();
  });

  it('returns 100 when only gains', () => {
    const values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];
    const result = computeRSI(values, 14);
    expect(result[result.length - 1]).toBe(100);
  });
});

describe('buildStandaloneChartData', () => {
  it('adds overlay keys to chart points', () => {
    const observations = [
      { obs_date: '2024-01-01', value: 10 },
      { obs_date: '2024-02-01', value: 20 },
      { obs_date: '2024-03-01', value: 30 },
    ];
    const data = buildStandaloneChartData(observations, [
      { id: '1', type: 'sma', period: 2 },
    ]);
    const key = trendSeriesKey('sma', 2);
    expect(data[0][key]).toBeNull();
    expect(data[1][key]).toBe(15);
    expect(data[2][key]).toBe(25);
  });
});
