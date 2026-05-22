import { describe, expect, it } from 'vitest';
import {
  buildBacktestQuery,
  buildEquityChartData,
  formatBacktestDrawdown,
  formatBacktestPct,
  formatBacktestProfitFactor,
  performanceMetricTone,
  sortTradesByExit,
  summarizePerformanceLabels,
  summarizeReturnMetrics,
} from '../utils/backtestData';

const sampleMetrics = {
  total_return_pct: 10,
  benchmark_return_pct: 8,
  alpha_pct: 2,
  cagr_pct: 5,
  max_drawdown_pct: 3,
  sharpe_ratio: 1.1,
  sortino_ratio: 1.6,
  profit_factor: 1.8,
  calmar_ratio: 1.67,
  win_rate_pct: 55,
  trade_count: 4,
  final_equity: 11000,
  initial_cash: 10000,
};

describe('backtestData utils', () => {
  it('formats percentage values', () => {
    expect(formatBacktestPct(12.345)).toBe('+12.35%');
    expect(formatBacktestPct(-3)).toBe('-3.00%');
    expect(formatBacktestPct(null)).toBe('—');
  });

  it('formats drawdown as a negative magnitude', () => {
    expect(formatBacktestDrawdown(7.8)).toBe('−7.80%');
    expect(formatBacktestDrawdown(0)).toBe('0.00%');
    expect(formatBacktestDrawdown(null)).toBe('—');
  });

  it('formats profit factor sentinel as infinity', () => {
    expect(formatBacktestProfitFactor(999)).toBe('∞');
    expect(formatBacktestProfitFactor(1.8)).toBe('1.80');
    expect(formatBacktestProfitFactor(null)).toBe('—');
  });

  it('builds backtest query from date range', () => {
    expect(buildBacktestQuery({ start: '2024-01-01', end: '2024-06-01' })).toEqual({
      start: '2024-01-01',
      end: '2024-06-01',
    });
  });

  it('merges strategy and benchmark equity curves by date', () => {
    const data = buildEquityChartData(
      [{ date: '2024-01-01', equity: 10000, cash: 0, shares: 1, drawdown_pct: 0 }],
      [{ date: '2024-01-01', equity: 10000, cash: 0, shares: 1, drawdown_pct: 0 }],
    );
    expect(data).toHaveLength(1);
    expect(data[0].strategy).toBe(10000);
    expect(data[0].benchmark).toBe(10000);
  });

  it('summarizes return metrics without risk-adjusted cards', () => {
    const rows = summarizeReturnMetrics(sampleMetrics);
    expect(rows.map((row) => row.key)).toEqual([
      'total_return_pct',
      'alpha_pct',
      'cagr_pct',
      'final_equity',
      'trade_count',
    ]);
    expect(rows.find((row) => row.key === 'trade_count')?.value).toBe('4');
  });

  it('summarizes performance labels with six pills', () => {
    const rows = summarizePerformanceLabels(sampleMetrics);
    expect(rows).toHaveLength(6);
    expect(rows.find((row) => row.key === 'sharpe_ratio')?.value).toBe('1.10');
    expect(rows.find((row) => row.key === 'profit_factor')?.value).toBe('1.80');
    expect(rows.find((row) => row.key === 'max_drawdown_pct')?.value).toBe('−3.00%');
  });

  it('shows infinity profit factor when backend reports no-loss sentinel', () => {
    const rows = summarizePerformanceLabels({ ...sampleMetrics, profit_factor: 999 });
    expect(rows.find((row) => row.key === 'profit_factor')?.value).toBe('∞');
    expect(rows.find((row) => row.key === 'profit_factor')?.tone).toBe('good');
  });

  it('marks trade-dependent labels unknown when no trades', () => {
    const rows = summarizePerformanceLabels({ ...sampleMetrics, trade_count: 0 });
    expect(rows.find((row) => row.key === 'profit_factor')?.tone).toBe('unknown');
    expect(rows.find((row) => row.key === 'win_rate_pct')?.tone).toBe('unknown');
  });

  it('sorts trades by exit date descending', () => {
    const sorted = sortTradesByExit([
      {
        entry_date: '2024-01-01',
        exit_date: '2024-02-01',
        entry_price: 100,
        exit_price: 110,
        shares: 10,
        pnl: 100,
        pnl_pct: 10,
      },
      {
        entry_date: '2024-03-01',
        exit_date: '2024-04-01',
        entry_price: 100,
        exit_price: 90,
        shares: 10,
        pnl: -100,
        pnl_pct: -10,
      },
    ]);
    expect(sorted[0].exit_date).toBe('2024-04-01');
  });
});

describe('performanceMetricTone', () => {
  it('classifies sharpe thresholds', () => {
    expect(performanceMetricTone('sharpe_ratio', 0.3)).toBe('bad');
    expect(performanceMetricTone('sharpe_ratio', 0.7)).toBe('neutral');
    expect(performanceMetricTone('sharpe_ratio', 1.2)).toBe('good');
  });

  it('classifies no-loss profit factor as good', () => {
    expect(performanceMetricTone('profit_factor', 999)).toBe('good');
  });

  it('classifies max drawdown with lower-is-better logic', () => {
    expect(performanceMetricTone('max_drawdown_pct', 25)).toBe('bad');
    expect(performanceMetricTone('max_drawdown_pct', 15)).toBe('neutral');
    expect(performanceMetricTone('max_drawdown_pct', 5)).toBe('good');
  });

  it('returns unknown for null values', () => {
    expect(performanceMetricTone('sortino_ratio', null)).toBe('unknown');
  });
});

describe('backtest API paths', () => {
  const BACKTEST_PATHS = [
    '/backtest/strategies',
    '/backtest/run',
    '/backtest/{id}/results',
  ];

  it('defines unique backtest endpoints', () => {
    expect(new Set(BACKTEST_PATHS).size).toBe(BACKTEST_PATHS.length);
  });
});
