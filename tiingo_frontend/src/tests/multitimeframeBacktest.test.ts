import { describe, expect, it } from 'vitest';
import type { BacktestResultsResponse } from '../api/backtestTypes';
import { buildOhlcvQuery } from '../constants/timeframes';
import {
  apiRangeFromOhlcvQuery,
  chartDateRange,
  collectResultSignalTimeframes,
  effectiveSignalTimeframe,
} from '../utils/multitimeframeBacktest';

describe('effectiveSignalTimeframe', () => {
  it('defaults to decision timeframe when leg signal is omitted', () => {
    expect(effectiveSignalTimeframe(undefined, '15m')).toBe('15m');
    expect(effectiveSignalTimeframe('', '1d')).toBe('1d');
  });

  it('keeps explicit leg signal timeframe', () => {
    expect(effectiveSignalTimeframe('30m', '15m')).toBe('30m');
  });
});

describe('collectResultSignalTimeframes', () => {
  const baseResults = {
    strategy: 'sma_crossover',
    params: { fast_period: 20, slow_period: 50 },
    start_date: '2024-01-02T09:30:00Z',
    end_date: '2024-01-05T16:00:00Z',
  } as BacktestResultsResponse;

  it('includes decision and standalone signal timeframes', () => {
    const timeframes = collectResultSignalTimeframes(baseResults, '30m', '15m');
    expect(timeframes.sort()).toEqual(['15m', '30m']);
  });

  it('deduplicates ensemble leg signal timeframes', () => {
    const ensembleResults = {
      ...baseResults,
      strategy: 'strategy_ensemble',
      params: {
        combine_mode: 'majority',
        threshold: 0.5,
        legs: [
          { strategy_id: 'sma_crossover', signal_timeframe: '5m', params: {}, weight: 1 },
          { strategy_id: 'rsi_reversion', signal_timeframe: '30m', params: {}, weight: 1 },
          { strategy_id: 'ema_crossover', params: {}, weight: 1 },
        ],
      },
    } as BacktestResultsResponse;

    const timeframes = collectResultSignalTimeframes(ensembleResults, '15m', '15m');
    expect([...timeframes].sort()).toEqual(['15m', '30m', '5m']);
  });
});

describe('chartDateRange', () => {
  it('prefers result bounds when present', () => {
    const range = chartDateRange(
      {
        start_date: '2024-01-02T09:30:00Z',
        end_date: '2024-01-05T16:00:00Z',
      } as BacktestResultsResponse,
      { preset: '1M', start: '2024-01-01', end: '2024-02-01' },
    );
    expect(range.start).toBe('2024-01-02T09:30:00Z');
    expect(range.end).toBe('2024-01-05T16:00:00Z');
  });
});

describe('buildOhlcvQuery integration', () => {
  it('builds intraday query params for API calls', () => {
    const query = buildOhlcvQuery('15m', {
      preset: '1W',
      start: '2024-01-02T09:30:00Z',
      end: '2024-01-05T16:00:00Z',
    });
    expect(query.timeframe).toBe('15m');
    expect(apiRangeFromOhlcvQuery(query)).toEqual({
      start: query.start,
      end: query.end,
    });
  });
});
