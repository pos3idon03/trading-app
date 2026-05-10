import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import BacktestResultCard from '../components/BacktestResultCard';
import type { BacktestResponse } from '../api/types';

vi.mock('recharts', () => ({
  AreaChart: ({ children }: { children: React.ReactNode }) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
}));

const baseResult: BacktestResponse = {
  backtest_id: 42,
  asset_id: 1,
  strategy_name: 'ma_crossover',
  status: 'completed',
  duration_ms: 123,
};

describe('BacktestResultCard', () => {
  it('renders the strategy label', () => {
    render(<BacktestResultCard result={baseResult} />);
    expect(screen.getByText(/MA Crossover/i)).toBeInTheDocument();
  });

  it('renders the backtest id and duration', () => {
    render(<BacktestResultCard result={baseResult} />);
    expect(screen.getByText(/#42/)).toBeInTheDocument();
    expect(screen.getByText(/123ms/)).toBeInTheDocument();
  });

  it('renders metrics when provided', () => {
    const result: BacktestResponse = {
      ...baseResult,
      metrics: {
        total_return: 0.25,
        sharpe_ratio: 1.5,
        max_drawdown: -0.1,
        win_rate: 0.6,
        profit_factor: 1.8,
        num_trades: 40,
      },
    };
    render(<BacktestResultCard result={result} />);
    expect(screen.getByText('Total Return')).toBeInTheDocument();
    expect(screen.getByText('25.00%')).toBeInTheDocument();
    expect(screen.getByText('Sharpe Ratio')).toBeInTheDocument();
  });

  it('renders error message when present', () => {
    const result: BacktestResponse = { ...baseResult, error_message: 'Something broke' };
    render(<BacktestResultCard result={result} />);
    expect(screen.getByText(/Something broke/)).toBeInTheDocument();
  });

  it('renders equity curve when data is provided', () => {
    const result: BacktestResponse = {
      ...baseResult,
      equity_curve: [
        { time: '2022-01-01', value: 100000 },
        { time: '2022-01-02', value: 101000 },
      ],
    };
    render(<BacktestResultCard result={result} />);
    expect(screen.getByTestId('area-chart')).toBeInTheDocument();
  });

  it('does not render equity curve when no data', () => {
    render(<BacktestResultCard result={{ ...baseResult, equity_curve: [] }} />);
    expect(screen.queryByTestId('area-chart')).not.toBeInTheDocument();
  });
});
