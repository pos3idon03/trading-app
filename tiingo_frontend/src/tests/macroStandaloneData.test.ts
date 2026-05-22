import { describe, expect, it } from 'vitest';
import {
  alignAssetToMacroDates,
  buildPeriodChangeContext,
  buildPeriodChangeSeries,
  buildSliderYearTicks,
  computePercentileRank,
  formatScatterTooltipLines,
  getSliderSteps,
  resolveMacroStep,
} from '../utils/macroStandaloneData';

describe('resolveMacroStep', () => {
  it('maps known FRED frequencies', () => {
    expect(resolveMacroStep('Monthly')).toBe('monthly');
    expect(resolveMacroStep('Weekly')).toBe('weekly');
    expect(resolveMacroStep('Daily')).toBe('daily');
  });

  it('infers monthly from observation gaps', () => {
    const observations = [
      { obs_date: '2024-01-01', value: 1 },
      { obs_date: '2024-02-01', value: 2 },
      { obs_date: '2024-03-01', value: 3 },
    ];
    expect(resolveMacroStep(undefined, observations)).toBe('monthly');
  });
});

describe('alignAssetToMacroDates', () => {
  it('uses nearest prior asset price for each macro date', () => {
    const macro = [
      { obs_date: '2024-01-15', value: 100 },
      { obs_date: '2024-02-15', value: 110 },
    ];
    const asset = [
      { date: '2024-01-10', value: 50 },
      { date: '2024-01-20', value: 55 },
      { date: '2024-02-14', value: 60 },
    ];
    const aligned = alignAssetToMacroDates(macro, asset);
    expect(aligned).toEqual([
      { date: '2024-01-15', macroValue: 100, assetValue: 50 },
      { date: '2024-02-15', macroValue: 110, assetValue: 60 },
    ]);
  });
});

describe('buildPeriodChangeSeries', () => {
  it('computes period-over-period percent changes', () => {
    const aligned = [
      { date: '2024-01-01', macroValue: 100, assetValue: 200 },
      { date: '2024-02-01', macroValue: 110, assetValue: 220 },
      { date: '2024-03-01', macroValue: 99, assetValue: 198 },
    ];
    const changes = buildPeriodChangeSeries(aligned);
    expect(changes).toHaveLength(2);
    expect(changes[0].macroChange).toBeCloseTo(10, 5);
    expect(changes[0].assetChange).toBeCloseTo(10, 5);
    expect(changes[1].macroChange).toBeCloseTo(-10, 5);
    expect(changes[1].assetChange).toBeCloseTo(-10, 5);
  });
});

describe('computePercentileRank', () => {
  it('returns rank within historical distribution', () => {
    expect(computePercentileRank(5, [1, 2, 3, 4, 10])).toBe(80);
    expect(computePercentileRank(1, [1, 2, 3, 4, 10])).toBe(0);
  });
});

describe('getSliderSteps', () => {
  it('returns number of change points', () => {
    const series = buildPeriodChangeSeries([
      { date: '2024-01-01', macroValue: 1, assetValue: 1 },
      { date: '2024-02-01', macroValue: 2, assetValue: 2 },
      { date: '2024-03-01', macroValue: 3, assetValue: 3 },
    ]);
    expect(getSliderSteps(series)).toBe(2);
  });
});

describe('buildPeriodChangeContext', () => {
  it('builds percentile context for selected index', () => {
    const series = buildPeriodChangeSeries([
      { date: '2024-01-01', macroValue: 100, assetValue: 100 },
      { date: '2024-02-01', macroValue: 110, assetValue: 120 },
      { date: '2024-03-01', macroValue: 120, assetValue: 90 },
    ]);
    const context = buildPeriodChangeContext(series, 1);
    expect(context?.point.date).toBe('2024-03-01');
    expect(context?.macroHistory).toHaveLength(2);
    expect(context?.assetPercentile).toBeGreaterThanOrEqual(0);
  });
});

describe('buildSliderYearTicks', () => {
  it('returns first index per year with percent positions', () => {
    const series = [
      { date: '2020-01-01', macroChange: 1, assetChange: 1 },
      { date: '2020-06-01', macroChange: 2, assetChange: 2 },
      { date: '2021-01-01', macroChange: 3, assetChange: 3 },
      { date: '2022-01-01', macroChange: 4, assetChange: 4 },
    ];
    const ticks = buildSliderYearTicks(series);
    expect(ticks[0]).toEqual({ year: 2020, index: 0, percent: 0 });
    expect(ticks.find((t) => t.year === 2021)?.index).toBe(2);
    expect(ticks[ticks.length - 1].year).toBe(2022);
  });

  it('subsamples when many years are present', () => {
    const series = Array.from({ length: 40 }, (_, i) => ({
      date: `${1987 + i}-01-01`,
      macroChange: i,
      assetChange: i,
    }));
    const ticks = buildSliderYearTicks(series);
    expect(ticks.length).toBeLessThanOrEqual(20);
    expect(ticks[0].year).toBe(1987);
    expect(ticks[ticks.length - 1].year).toBe(2026);
  });
});

describe('formatScatterTooltipLines', () => {
  it('formats period and change lines', () => {
    const lines = formatScatterTooltipLines(
      { date: '2016-12-22', macroChange: 1.05, assetChange: -0.28 },
      'DCOILWTICO',
      'QQQ',
    );
    expect(lines.period).toBe('2016-12-22');
    expect(lines.macroLine).toBe('DCOILWTICO Δ%: +1.05%');
    expect(lines.assetLine).toBe('QQQ Δ%: -0.28%');
  });
});
