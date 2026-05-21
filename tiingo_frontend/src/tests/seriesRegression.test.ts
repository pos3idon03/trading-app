import { describe, expect, it } from 'vitest';
import {
  MIN_REGRESSION_SAMPLE,
  alignSeriesDaily,
  computeRegressionMatrix,
} from '../utils/seriesRegression';
import type { SeriesInput } from '../utils/seriesRegression';

function linearSeries(id: string, start: number, step: number, count: number): SeriesInput {
  const points = Array.from({ length: count }, (_, i) => {
    const day = String(i + 1).padStart(2, '0');
    return { date: `2024-01-${day}`, value: start + step * i };
  });
  return { id, label: id, points };
}

describe('alignSeriesDaily', () => {
  it('forward-fills macro onto daily instrument dates', () => {
    const macro: SeriesInput = {
      id: 'GDP',
      label: 'GDP',
      points: [
        { date: '2024-01-01', value: 100 },
        { date: '2024-01-03', value: 110 },
      ],
    };
    const stock: SeriesInput = {
      id: 'MSFT',
      label: 'MSFT',
      points: [
        { date: '2024-01-01', value: 10 },
        { date: '2024-01-02', value: 11 },
        { date: '2024-01-03', value: 12 },
      ],
    };
    const { dates, aligned } = alignSeriesDaily([macro, stock]);
    expect(dates).toEqual(['2024-01-01', '2024-01-02', '2024-01-03']);
    expect(aligned[0]).toEqual([100, 10]);
    expect(aligned[1]).toEqual([100, 11]);
    expect(aligned[2]).toEqual([110, 12]);
  });
});

describe('computeRegressionMatrix', () => {
  it('returns null when sample is below minimum', () => {
    const a = linearSeries('A', 1, 0.1, MIN_REGRESSION_SAMPLE - 1);
    const b = linearSeries('B', 2, 0.2, MIN_REGRESSION_SAMPLE - 1);
    expect(computeRegressionMatrix([a, b], 'level_pearson')).toBeNull();
  });

  it('computes perfect positive correlation on levels', () => {
    const count = MIN_REGRESSION_SAMPLE + 5;
    const a = linearSeries('A', 1, 1, count);
    const b = linearSeries('B', 2, 2, count);
    const result = computeRegressionMatrix([a, b], 'level_pearson');
    expect(result).not.toBeNull();
    expect(result!.values[0][1]).toBeCloseTo(1, 5);
    expect(result!.values[1][0]).toBeCloseTo(1, 5);
    expect(result!.sampleSize).toBeGreaterThanOrEqual(MIN_REGRESSION_SAMPLE);
  });

  it('produces symmetric OLS R² matrix', () => {
    const count = MIN_REGRESSION_SAMPLE + 5;
    const a = linearSeries('A', 1, 0.5, count);
    const b = linearSeries('B', 3, 1.2, count);
    const result = computeRegressionMatrix([a, b], 'ols_r2');
    expect(result).not.toBeNull();
    expect(result!.values[0][1]).toBe(result!.values[1][0]);
    expect(result!.values[0][0]).toBe(1);
  });
});
