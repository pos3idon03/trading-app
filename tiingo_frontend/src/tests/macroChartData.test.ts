import { describe, expect, it } from 'vitest';
import {
  computeMacroCompareMeta,
  formatMacroCompareSubtitle,
  getObservationBounds,
  mergeMacroSeries,
} from '../utils/macroChartData';

describe('mergeMacroSeries', () => {
  it('returns primary-only points sorted by date', () => {
    const primary = [
      { obs_date: '2024-02-01', value: 2 },
      { obs_date: '2024-01-01', value: 1 },
    ];
    const result = mergeMacroSeries(primary);
    expect(result).toEqual([
      { date: '2024-01-01', primary: 1 },
      { date: '2024-02-01', primary: 2 },
    ]);
  });

  it('outer-joins compare series without forward-fill', () => {
    const primary = [
      { obs_date: '2024-01-01', value: 1 },
      { obs_date: '2024-03-01', value: 3 },
    ];
    const compare = [
      { obs_date: '2024-02-01', value: 20 },
      { obs_date: '2024-03-01', value: 30 },
    ];
    const result = mergeMacroSeries(primary, compare);
    expect(result).toEqual([
      { date: '2024-01-01', primary: 1 },
      { date: '2024-02-01', compare: 20 },
      { date: '2024-03-01', primary: 3, compare: 30 },
    ]);
  });

  it('outer-joins mixed-frequency daily and weekly series', () => {
    const primary = [
      { obs_date: '2024-01-01', value: 1 },
      { obs_date: '2024-01-02', value: 2 },
      { obs_date: '2024-01-03', value: 3 },
    ];
    const compare = [{ obs_date: '2024-01-02', value: 20 }];
    const result = mergeMacroSeries(primary, compare);
    expect(result).toHaveLength(3);
    expect(result[1]).toEqual({ date: '2024-01-02', primary: 2, compare: 20 });
  });

  it('handles null values', () => {
    const primary = [{ obs_date: '2024-01-01', value: null }];
    const result = mergeMacroSeries(primary);
    expect(result[0].primary).toBeNull();
  });
});

describe('getObservationBounds', () => {
  it('returns null for empty observations', () => {
    expect(getObservationBounds([])).toBeNull();
  });

  it('returns start and end dates', () => {
    const obs = [
      { obs_date: '1991-09-02', value: 1 },
      { obs_date: '1987-01-05', value: 2 },
      { obs_date: '2024-05-01', value: 3 },
    ];
    expect(getObservationBounds(obs)).toEqual({
      start: '1987-01-05',
      end: '2024-05-01',
    });
  });
});

describe('computeMacroCompareMeta', () => {
  const primary = [
    { obs_date: '1987-01-05', value: 1 },
    { obs_date: '2024-05-01', value: 2 },
  ];
  const compare = [
    { obs_date: '1991-09-02', value: 10 },
    { obs_date: '2024-04-01', value: 20 },
  ];

  it('computes union and overlap spans', () => {
    const meta = computeMacroCompareMeta(primary, compare);
    expect(meta).toEqual({
      chartStart: '1987-01-05',
      chartEnd: '2024-05-01',
      overlapStart: '1991-09-02',
      overlapEnd: '2024-04-01',
      primaryCount: 2,
      compareCount: 2,
    });
  });

  it('clips union and overlap to filter', () => {
    const meta = computeMacroCompareMeta(primary, compare, {
      start: '1990-01-01',
      end: '2020-01-01',
    });
    expect(meta).toEqual({
      chartStart: '1990-01-01',
      chartEnd: '2020-01-01',
      overlapStart: '1991-09-02',
      overlapEnd: '2020-01-01',
      primaryCount: 2,
      compareCount: 2,
    });
  });

  it('returns primary-only meta when compare is absent', () => {
    const meta = computeMacroCompareMeta(primary);
    expect(meta?.overlapStart).toBeNull();
    expect(meta?.chartStart).toBe('1987-01-05');
    expect(meta?.compareCount).toBe(0);
  });
});

describe('formatMacroCompareSubtitle', () => {
  it('formats compare mode with overlap', () => {
    const meta = {
      chartStart: '1987-01-05',
      chartEnd: '2024-05-01',
      overlapStart: '1991-09-02',
      overlapEnd: '2024-04-01',
      primaryCount: 9655,
      compareCount: 1860,
    };
    const text = formatMacroCompareSubtitle('DCOILWTICO', meta, 'GASREGW', 'MAX');
    expect(text).toContain('DCOILWTICO (9655) vs GASREGW (1860)');
    expect(text).toContain('1987-01 → 2024-05');
    expect(text).toContain('overlap 1991-09 → 2024-04');
    expect(text).toContain('MAX');
  });
});
