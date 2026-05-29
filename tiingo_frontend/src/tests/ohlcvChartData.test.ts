import { describe, expect, it } from 'vitest';
import { buildCandleData, buildCloseLineData, buildVolumeData, normalizeChartTime } from '../utils/ohlcvChartData';

describe('ohlcvChartData', () => {
  it('normalizes daily bars to UTC date strings', () => {
    expect(normalizeChartTime('2026-02-20T00:00:00.000Z', '1d')).toBe('2026-02-20');
    expect(normalizeChartTime('2026-02-20T14:30:00.000Z', '1d')).toBe('2026-02-20');
  });

  it('deduplicates daily bars that share the same calendar day', () => {
    const records = [
      { time: '2026-02-20T00:00:00.000Z', open: 1, high: 2, low: 0.5, close: 1.5, volume: 10, source: 'a' },
      { time: '2026-02-20T14:00:00.000Z', open: 3, high: 4, low: 2.5, close: 3.5, volume: 20, source: 'a' },
      { time: '2026-02-21T00:00:00.000Z', open: 5, high: 6, low: 4.5, close: 5.5, volume: 30, source: 'a' },
    ];
    const data = buildCandleData(records, '1d');
    expect(data).toHaveLength(2);
    expect(data[0].time).toBe('2026-02-20');
    expect(data[0].close).toBe(3.5);
    expect(data[1].time).toBe('2026-02-21');
  });

  it('deduplicates intraday bars with the same unix timestamp', () => {
    const ts = '2026-02-20T14:00:00.000Z';
    const records = [
      { time: ts, open: 1, high: 2, low: 0.5, close: 1.5, volume: 10, source: 'a' },
      { time: ts, open: 2, high: 3, low: 1.5, close: 2.5, volume: 11, source: 'a' },
    ];
    const data = buildCandleData(records, '5m');
    expect(data).toHaveLength(1);
    expect(data[0].close).toBe(2.5);
  });

  it('builds close line data from candle closes', () => {
    const records = [
      { time: '2026-02-20T00:00:00.000Z', open: 1, high: 2, low: 0.5, close: 1.5, volume: 10, source: 'a' },
      { time: '2026-02-21T00:00:00.000Z', open: 2, high: 3, low: 1.5, close: 2.5, volume: 11, source: 'a' },
    ];
    const line = buildCloseLineData(records, '1d');
    expect(line).toEqual([
      { time: '2026-02-20', value: 1.5 },
      { time: '2026-02-21', value: 2.5 },
    ]);
  });

  it('applies style preset colors to volume bars', () => {
    const records = [
      { time: '2024-01-02T00:00:00Z', open: 10, high: 11, low: 9, close: 10.5, volume: 1000, source: 'a' },
    ];
    const volume = buildVolumeData(records, '1d', 'blueOrange');
    expect(volume[0].color).toContain('3b82f6');
  });
});
