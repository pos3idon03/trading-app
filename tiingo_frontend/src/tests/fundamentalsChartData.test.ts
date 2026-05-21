import { describe, expect, it } from 'vitest';
import {
  buildFundamentalsSeries,
  formatFundamentalValue,
  metricsWithChartData,
} from '../utils/fundamentalsChartData';
import type { FundamentalMetric } from '../api/types';

const sample: FundamentalMetric[] = [
  { time: '2024-06-30T00:00:00Z', metric_name: 'revenue', value: 200, period: '2024-Q2', statement_type: 'incomeStatement' },
  { time: '2024-03-31T00:00:00Z', metric_name: 'revenue', value: 100, period: '2024-Q1', statement_type: 'incomeStatement' },
  { time: '2024-03-31T00:00:00Z', metric_name: 'eps', value: 1.2, period: '2024-Q1', statement_type: 'incomeStatement' },
];

describe('buildFundamentalsSeries', () => {
  it('filters and sorts by time ascending', () => {
    const series = buildFundamentalsSeries(sample, 'revenue');
    expect(series).toHaveLength(2);
    expect(series[0].period).toBe('2024-Q1');
    expect(series[1].period).toBe('2024-Q2');
  });
});

describe('metricsWithChartData', () => {
  it('requires at least two points per metric', () => {
    const withData = metricsWithChartData(sample, ['revenue', 'eps']);
    expect(withData.has('revenue')).toBe(true);
    expect(withData.has('eps')).toBe(false);
  });
});

describe('formatFundamentalValue', () => {
  it('formats large currency values', () => {
    expect(formatFundamentalValue(1_500_000_000, 'currency')).toBe('$1.50B');
  });

  it('formats percent', () => {
    expect(formatFundamentalValue(0.15, 'percent')).toBe('15.00%');
  });
});
