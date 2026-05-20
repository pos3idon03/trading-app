import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  defaultCalibrationDaysForTimeframe,
  defaultDatesForTimeframe,
  DEFAULT_BACKTEST_YEARS,
  isIntradayTimeframe,
} from './backtestDates';

describe('defaultDatesForTimeframe', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('uses today as end and today minus years as start for daily', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-15T12:00:00'));

    const { start, end } = defaultDatesForTimeframe('1d');
    expect(end).toBe('2026-05-15');
    expect(start).toBe('2023-05-15');
  });

  it('uses the same daily window for weekly', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-15T12:00:00'));

    const { start, end } = defaultDatesForTimeframe('1w');
    expect(end).toBe('2026-05-15');
    expect(start).toBe('2023-05-15');
  });

  it('respects a custom years argument', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-15T12:00:00'));

    const { start } = defaultDatesForTimeframe('1d', 5);
    expect(start).toBe('2021-05-15');
  });

  it('uses 30-day lookback for short intraday timeframes', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-15T12:00:00'));

    const { start, end } = defaultDatesForTimeframe('5m');
    expect(end).toBe('2026-05-15');
    expect(start).toBe('2026-04-15');
  });

  it('exports DEFAULT_BACKTEST_YEARS as 3', () => {
    expect(DEFAULT_BACKTEST_YEARS).toBe(3);
  });

  it('defaultCalibrationDaysForTimeframe returns day-scale windows', () => {
    expect(defaultCalibrationDaysForTimeframe('15m')).toBe(30);
    expect(defaultCalibrationDaysForTimeframe('1h')).toBe(60);
    expect(isIntradayTimeframe('15m')).toBe(true);
    expect(isIntradayTimeframe('1d')).toBe(false);
  });
});
