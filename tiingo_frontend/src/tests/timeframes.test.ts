import { describe, expect, it } from 'vitest';
import {
  buildOhlcvQuery,
  normalizeDateRangeForApi,
  DAILY_PLUS_BAR_LIMIT,
  INTRADAY_BAR_LIMIT,
  toDailyApiRange,
  type DateRangeValue,
} from '../constants/timeframes';

describe('buildOhlcvQuery', () => {
  it('loads max history for daily plus when MAX preset', () => {
    expect(buildOhlcvQuery('1d', { preset: 'MAX' })).toEqual({
      timeframe: '1d',
      limit: DAILY_PLUS_BAR_LIMIT,
    });
    expect(buildOhlcvQuery('1w', { preset: 'MAX' }).limit).toBe(DAILY_PLUS_BAR_LIMIT);
  });

  it('passes date range for daily plus presets', () => {
    const range: DateRangeValue = { preset: '1Y', start: '2024-01-01', end: '2025-01-01' };
    expect(buildOhlcvQuery('1d', range)).toEqual({
      timeframe: '1d',
      limit: DAILY_PLUS_BAR_LIMIT,
      start: '2024-01-01T00:00:00Z',
      end: '2025-01-01T23:59:59Z',
    });
  });

  it('loads 3000 bars for intraday MAX', () => {
    expect(buildOhlcvQuery('15m', { preset: 'MAX' })).toEqual({
      timeframe: '15m',
      limit: INTRADAY_BAR_LIMIT,
    });
  });

  it('passes date range for intraday presets', () => {
    const range: DateRangeValue = { preset: '5D', start: '2024-01-01T00:00:00.000Z', end: '2024-01-06T00:00:00.000Z' };
    expect(buildOhlcvQuery('5m', range)).toEqual({
      timeframe: '5m',
      limit: INTRADAY_BAR_LIMIT,
      start: range.start,
      end: range.end,
    });
  });
});

describe('normalizeDateRangeForApi', () => {
  it('fills missing end date for open-ended custom ranges', () => {
    const normalized = normalizeDateRangeForApi(
      { preset: 'MAX', start: '2020-01-01' },
      '1d',
    );
    expect(normalized.start).toBe('2020-01-01');
    expect(normalized.end).toBeTruthy();
  });
});

describe('toDailyApiRange', () => {
  it('expands date-only bounds to full calendar days', () => {
    expect(toDailyApiRange({ preset: '1Y', start: '2024-06-01', end: '2025-06-01' })).toEqual({
      start: '2024-06-01T00:00:00Z',
      end: '2025-06-01T23:59:59Z',
    });
  });
});
