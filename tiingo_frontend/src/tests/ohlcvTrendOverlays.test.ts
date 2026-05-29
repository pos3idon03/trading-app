import { describe, expect, it } from 'vitest';
import {
  buildOhlcvOverlayLines,
  hasOverlay,
} from '../utils/ohlcvTrendOverlays';

const records = [
  { time: '2024-01-01T00:00:00Z', open: 10, high: 11, low: 9, close: 10, volume: 100, source: 'a' },
  { time: '2024-01-02T00:00:00Z', open: 10, high: 12, low: 9.5, close: 11, volume: 110, source: 'a' },
  { time: '2024-01-03T00:00:00Z', open: 11, high: 13, low: 10.5, close: 12, volume: 120, source: 'a' },
  { time: '2024-01-04T00:00:00Z', open: 12, high: 14, low: 11.5, close: 13, volume: 130, source: 'a' },
];

describe('buildOhlcvOverlayLines', () => {
  it('aligns SMA points to chart times and skips warm-up bars', () => {
    const lines = buildOhlcvOverlayLines(records, '1d', [
      { id: 'sma2', type: 'sma', period: 2 },
    ]);

    expect(lines).toHaveLength(1);
    expect(lines[0].key).toBe('sma_2');
    expect(lines[0].points).toHaveLength(3);
    expect(lines[0].points[0]).toEqual({ time: '2024-01-02', value: 10.5 });
    expect(lines[0].points[2]).toEqual({ time: '2024-01-04', value: 12.5 });
  });

  it('builds EMA overlay series', () => {
    const lines = buildOhlcvOverlayLines(records, '1d', [
      { id: 'ema2', type: 'ema', period: 2 },
    ]);

    expect(lines[0].key).toBe('ema_2');
    expect(lines[0].points[0].value).toBe(10.5);
  });
});

describe('hasOverlay', () => {
  it('detects duplicate overlay configs', () => {
    const overlays = [{ id: 'a', type: 'sma' as const, period: 20 }];
    expect(hasOverlay(overlays, 'sma', 20)).toBe(true);
    expect(hasOverlay(overlays, 'ema', 20)).toBe(false);
  });
});
