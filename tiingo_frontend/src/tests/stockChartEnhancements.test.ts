import { describe, expect, it } from 'vitest';
import {
  buildCorporateActionMarkers,
  buildVolumeData,
  formatSplitTooltip,
} from '../utils/ohlcvChartData';
import { formatPerformancePct, formatExampleOutcome, performanceCardClass } from '../utils/stockPerformance';
import { formatKpiValue } from '../utils/stockKpis';

describe('buildVolumeData', () => {
  it('colors volume bars by candle direction', () => {
    const records = [
      { time: '2024-01-02T00:00:00Z', open: 10, high: 11, low: 9, close: 10.5, volume: 1000, source: 'a' },
      { time: '2024-01-03T00:00:00Z', open: 10.5, high: 11, low: 9, close: 10, volume: 800, source: 'a' },
    ];
    const volume = buildVolumeData(records, '1d');
    expect(volume).toHaveLength(2);
    expect(volume[0].color).toContain('22c55e');
    expect(volume[1].color).toContain('ef4444');
  });
});

describe('buildCorporateActionMarkers', () => {
  it('creates D and S markers on daily timeframe only', () => {
    const records = [
      {
        time: '2024-01-02T00:00:00Z',
        open: 1,
        high: 2,
        low: 0.5,
        close: 1.5,
        volume: 10,
        div_cash: 0.5,
        split_factor: 1,
        source: 'a',
      },
      {
        time: '2024-01-03T00:00:00Z',
        open: 1,
        high: 2,
        low: 0.5,
        close: 1.5,
        volume: 10,
        div_cash: 0,
        split_factor: 4,
        source: 'a',
      },
    ];
    const daily = buildCorporateActionMarkers(records, '1d');
    expect(daily).toHaveLength(2);
    expect(daily[0].text).toBe('D');
    expect(daily[1].text).toBe('S');

    const intraday = buildCorporateActionMarkers(records, '5m');
    expect(intraday).toHaveLength(0);
  });
});

describe('formatSplitTooltip', () => {
  it('formats split factor as ratio label', () => {
    expect(formatSplitTooltip(4)).toBe('Split 4:1');
  });
});

describe('stockPerformance utils', () => {
  it('formats positive and negative percentages', () => {
    expect(formatPerformancePct(8.17)).toBe('+8.17%');
    expect(formatPerformancePct(-4.88)).toBe('-4.88%');
    expect(formatPerformancePct(null)).toBe('—');
  });

  it('applies green/red card classes', () => {
    expect(performanceCardClass(1)).toContain('emerald');
    expect(performanceCardClass(-1)).toContain('red');
  });

  it('formats example outcome in instrument currency', () => {
    expect(formatExampleOutcome('USD', 100, 103.91)).toBe('$100.00 → $103.91');
    expect(formatExampleOutcome('EUR', 100, 97.5)).toBe('100,00\u00a0€ → 97,50\u00a0€');
    expect(formatExampleOutcome('USD', 100, null)).toBe('—');
  });
});

describe('stockKpis utils', () => {
  it('formats KPI values by format type', () => {
    expect(formatKpiValue({ key: 'pe', label: 'P/E', value: 25.5, format: 'ratio' })).toBe('25.50');
    expect(formatKpiValue({ key: 'dy', label: 'Yield', value: 2.1, format: 'percent' })).toBe('2.10%');
    expect(formatKpiValue({ key: 'eps', label: 'EPS', value: 3.25, format: 'perShare' })).toBe('$3.25');
  });
});
