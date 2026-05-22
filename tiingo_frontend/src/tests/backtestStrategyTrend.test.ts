import { describe, expect, it } from 'vitest';
import type { OHLCVBar } from '../api/types';
import {
  buildStrategyTrendChartData,
  strategyTrendChartMode,
  strategyTrendChartSubtitle,
  strategyTrendTitle,
  toChartDate,
} from '../utils/backtestStrategyTrend';

function bar(date: string, close: number): OHLCVBar {
  return {
    time: `${date}T00:00:00Z`,
    open: close,
    high: close + 1,
    low: close - 1,
    close,
    volume: 1000,
    source: 'tiingo_eod',
  };
}

describe('strategyTrendChartMode', () => {
  it('maps strategy ids to chart modes', () => {
    expect(strategyTrendChartMode('rsi_reversion')).toBe('rsi');
    expect(strategyTrendChartMode('stochastic_reversion')).toBe('rsi');
    expect(strategyTrendChartMode('mfi_reversion')).toBe('rsi');
    expect(strategyTrendChartMode('sma_crossover')).toBe('ma');
    expect(strategyTrendChartMode('donchian_breakout')).toBe('channel');
    expect(strategyTrendChartMode('bollinger_breakout')).toBe('bands');
    expect(strategyTrendChartMode('ts_momentum')).toBe('momentum');
    expect(strategyTrendChartMode('buy_and_hold')).toBeNull();
  });
});

describe('toChartDate', () => {
  it('uses date-only labels for daily timeframes', () => {
    expect(toChartDate('2024-01-02T09:30:00Z', '1d')).toBe('2024-01-02');
  });

  it('uses ISO datetime labels for intraday timeframes', () => {
    expect(toChartDate('2024-01-02T09:30:00.000Z', '15m')).toBe('2024-01-02T09:30:00Z');
  });
});

describe('buildStrategyTrendChartData', () => {
  it('builds rsi series with threshold bands', () => {
    const records = Array.from({ length: 20 }, (_, i) => bar(`2024-01-${String(i + 1).padStart(2, '0')}`, 10 + i));
    const data = buildStrategyTrendChartData('rsi_reversion', { period: 14, oversold: 30, overbought: 70 }, records);
    expect(data).not.toBeNull();
    expect(data?.[0].rsi).toBeNull();
    expect(data?.[14].rsi).not.toBeNull();
    expect(data?.[14].oversold).toBe(30);
    expect(data?.[14].overbought).toBe(70);
  });

  it('builds close and moving averages for sma crossover', () => {
    const records = Array.from({ length: 60 }, (_, i) => {
      const d = new Date(Date.UTC(2024, 0, 1));
      d.setUTCDate(d.getUTCDate() + i);
      return bar(d.toISOString().slice(0, 10), 100 + i);
    });
    const data = buildStrategyTrendChartData(
      'sma_crossover',
      { fast_period: 20, slow_period: 50 },
      records,
    );
    expect(data?.[49].close).toBe(149);
    expect(data?.[49].fast).not.toBeNull();
    expect(data?.[49].slow).not.toBeNull();
  });

  it('builds donchian channel series', () => {
    const records = Array.from({ length: 30 }, (_, i) => bar(`2024-01-${String(i + 1).padStart(2, '0')}`, 100 + i));
    const data = buildStrategyTrendChartData('donchian_breakout', { channel_period: 20 }, records);
    expect(data?.[19].upper).toBeNull();
    expect(data?.[20].upper).not.toBeNull();
    expect(data?.[20].lower).not.toBeNull();
  });

  it('builds bollinger band series', () => {
    const records = Array.from({ length: 30 }, (_, i) => {
      const d = new Date(Date.UTC(2024, 0, 1));
      d.setUTCDate(d.getUTCDate() + i);
      return bar(d.toISOString().slice(0, 10), 100 + i);
    });
    const data = buildStrategyTrendChartData('bollinger_breakout', { period: 20, std_dev: 2 }, records);
    expect(data?.[18].upper).toBeNull();
    expect(data?.[19].upper).not.toBeNull();
    expect(data?.[19].middle).not.toBeNull();
  });

  it('builds momentum return series', () => {
    const records = Array.from({ length: 80 }, (_, i) => {
      const d = new Date(Date.UTC(2024, 0, 1));
      d.setUTCDate(d.getUTCDate() + i);
      return bar(d.toISOString().slice(0, 10), 100 + i);
    });
    const data = buildStrategyTrendChartData('ts_momentum', { lookback: 63 }, records);
    expect(data?.[62].momentum).toBeNull();
    expect(data?.[63].momentum).not.toBeNull();
  });

  it('returns null for buy and hold', () => {
    expect(buildStrategyTrendChartData('buy_and_hold', {}, [bar('2024-01-01', 100)])).toBeNull();
  });
});

describe('strategyTrendChartSubtitle', () => {
  it('includes bar count, range, and MA warmup hint', () => {
    const records = [
      { time: '2024-01-01T12:00:00Z', open: 1, high: 1, low: 1, close: 1, volume: 0 },
      { time: '2024-01-02T12:00:00Z', open: 1, high: 1, low: 1, close: 1, volume: 0 },
    ];
    const subtitle = strategyTrendChartSubtitle(records, '4h', 'ema_crossover', {
      fast_period: 12,
      slow_period: 26,
    });
    expect(subtitle).toContain('2 bars');
    expect(subtitle).toContain('EMA warmup');
  });
});

describe('strategyTrendTitle', () => {
  it('formats titles from params', () => {
    expect(strategyTrendTitle('rsi_reversion', { period: 14 })).toBe('RSI (14)');
    expect(strategyTrendTitle('sma_crossover', { fast_period: 20, slow_period: 50 })).toBe('SMA 20 / 50');
    expect(strategyTrendTitle('donchian_breakout', { channel_period: 20 })).toBe('Donchian (20)');
    expect(strategyTrendTitle('bollinger_breakout', { period: 20, std_dev: 2 })).toBe('Bollinger 20 / 2');
    expect(strategyTrendTitle('ts_momentum', { lookback: 63 })).toBe('Momentum (63)');
  });
});
