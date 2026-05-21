import type { UTCTimestamp } from 'lightweight-charts';
import type { OHLCVBar } from '../api/types';
import { DAILY_PLUS_TIMEFRAMES, INTRADAY_TIMEFRAMES } from '../constants/timeframes';

export type ChartBar = {
  time: string | UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
};

export function normalizeChartTime(raw: string, timeframe: string): string | UTCTimestamp {
  if (INTRADAY_TIMEFRAMES.has(timeframe)) {
    return Math.floor(new Date(raw).getTime() / 1000) as UTCTimestamp;
  }
  return new Date(raw).toISOString().slice(0, 10);
}

export function buildCandleData(records: OHLCVBar[], timeframe: string): ChartBar[] {
  const sorted = [...records].sort((a, b) => a.time.localeCompare(b.time));
  const byTime = new Map<string | number, ChartBar>();

  for (const r of sorted) {
    const time = normalizeChartTime(r.time, timeframe);
    byTime.set(time, {
      time,
      open: r.open,
      high: r.high,
      low: r.low,
      close: r.close,
    });
  }

  return [...byTime.values()].sort((a, b) => (a.time > b.time ? 1 : a.time < b.time ? -1 : 0));
}

export function isDailyPlusChartTimeframe(timeframe: string): boolean {
  return DAILY_PLUS_TIMEFRAMES.has(timeframe);
}
