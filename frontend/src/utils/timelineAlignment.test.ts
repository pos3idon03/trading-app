import { describe, it, expect } from 'vitest';
import type { ComboStrategySignal } from '../api/types';
import {
  buildAlignedTimelineData,
  buildRawTimelineData,
  finestTimeframe,
  signalToValue,
} from './timelineAlignment';

function makeStrategy(
  name: string,
  timeline: { time: string; signal: string }[],
): ComboStrategySignal {
  return {
    strategy_name: name,
    trade_log: [],
    indicator_series: [],
    equity_curve: [],
    signal_timeline: timeline,
  };
}

describe('finestTimeframe', () => {
  it('returns shortest duration timeframe', () => {
    expect(finestTimeframe(['1h', '15m', '4h'])).toBe('15m');
  });
});

describe('buildRawTimelineData', () => {
  it('preserves only Buy/Sell values for directional strategies', () => {
    const ema = makeStrategy('ema_cross', [
      { time: '2026-05-15T10:00:00Z', signal: 'Sell' },
      { time: '2026-05-16T14:00:00Z', signal: 'Buy' },
    ]);
    const data = buildRawTimelineData(ema);
    expect(data.every((r) => r.ema_cross === 0 || r.ema_cross === 1)).toBe(true);
  });
});

describe('buildAlignedTimelineData', () => {
  it('puts both strategies on every grid row when timestamps differ', () => {
    const atr = makeStrategy('atr_trailing_stop', [
      { time: '2026-04-20T10:00:00Z', signal: 'Buy' },
      { time: '2026-04-20T10:15:00Z', signal: 'Sell' },
      { time: '2026-04-20T10:30:00Z', signal: 'Sell' },
    ]);
    const rsi = makeStrategy('rsi', [
      { time: '2026-04-20T10:00:00Z', signal: 'Neutral' },
      { time: '2026-04-20T11:00:00Z', signal: 'Buy' },
    ]);
    const data = buildAlignedTimelineData([atr, rsi], '15m');

    expect(data.length).toBeGreaterThan(0);
    for (const row of data) {
      expect(row.atr_trailing_stop).toBeDefined();
      expect(row.rsi).toBeDefined();
    }
  });

  it('forward-fills coarser leg onto finer grid', () => {
    const rsi = makeStrategy('rsi', [
      { time: '2026-04-20T10:00:00Z', signal: 'Buy' },
      { time: '2026-04-20T11:00:00Z', signal: 'Sell' },
    ]);
    const data = buildAlignedTimelineData([rsi], '15m');
    const at1030 = data.find((r) => r.time.includes('10:30') || new Date(r.time).getUTCMinutes() === 30);
    if (at1030) {
      expect(at1030.rsi).toBe(signalToValue('Buy'));
    }
  });
});
