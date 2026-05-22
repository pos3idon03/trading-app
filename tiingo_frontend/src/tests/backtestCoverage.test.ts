import { describe, expect, it } from 'vitest';
import {
  buildCoverageWarnings,
  parseEffectiveCoverage,
  requestedRangeStart,
  warmupRequirementBars,
} from '../utils/backtestCoverage';

describe('backtestCoverage', () => {
  it('parses effective coverage payload', () => {
    const parsed = parseEffectiveCoverage({
      timeframe: '4h',
      native: [],
      effective: {
        min_time: '2024-01-01T00:00:00Z',
        max_time: '2024-03-01T00:00:00Z',
        bar_count: 80,
        source: 'tiingo_iex',
        derived_from: '1h',
      },
    });
    expect(parsed?.effective?.bar_count).toBe(80);
    expect(parsed?.effective?.derived_from).toBe('1h');
  });

  it('warns when range starts before coverage', () => {
    const warnings = buildCoverageWarnings(
      {
        '4h': {
          timeframe: '4h',
          native: [],
          effective: {
            min_time: '2024-02-01T00:00:00Z',
            max_time: '2024-05-01T00:00:00Z',
            bar_count: 50,
            source: 'tiingo_iex',
            derived_from: '1h',
          },
        },
      },
      { preset: '3M', start: '2024-01-01T00:00:00Z', end: '2024-05-01T00:00:00Z' },
      { '4h': 27 },
    );
    expect(warnings.some((w) => w.timeframe === '4h')).toBe(true);
  });

  it('warns when bar count is below requirement', () => {
    const warnings = buildCoverageWarnings(
      {
        '4h': {
          timeframe: '4h',
          native: [],
          effective: {
            min_time: '2024-02-01T00:00:00Z',
            max_time: '2024-05-01T00:00:00Z',
            bar_count: 10,
            source: 'tiingo_iex',
            derived_from: null,
          },
        },
      },
      { preset: 'MAX' },
      { '4h': 27 },
    );
    expect(warnings[0].message).toContain('10');
  });

  it('computes warmup bars for ema crossover', () => {
    expect(warmupRequirementBars('ema_crossover', { slow_period: 26 })).toBe(27);
  });

  it('requestedRangeStart returns start when set', () => {
    expect(
      requestedRangeStart({ preset: '1M', start: '2024-01-01T00:00:00Z', end: '2024-02-01T00:00:00Z' }),
    ).toBe('2024-01-01T00:00:00Z');
  });
});
