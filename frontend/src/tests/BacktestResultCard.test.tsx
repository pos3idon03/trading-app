import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BacktestResultCard from '../components/BacktestResultCard';
import type { BacktestResponse } from '../api/types';

vi.mock('recharts', () => ({
  ComposedChart: ({ children }: { children: React.ReactNode }) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
  ReferenceDot: () => null,
  ReferenceLine: () => null,
  Legend: () => null,
}));

const baseResult: BacktestResponse = {
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

  it('renders duration but no backtest id', () => {
    render(<BacktestResultCard result={baseResult} />);
    expect(screen.getByText(/123ms/)).toBeInTheDocument();
    expect(screen.queryByText(/#\d+/)).not.toBeInTheDocument();
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
    expect(screen.getByText('1.500')).toBeInTheDocument();
    expect(screen.getByText('1.80')).toBeInTheDocument();
    expect(screen.getByRole('meter', { name: /Sharpe Ratio/i })).toBeInTheDocument();
    expect(screen.getByRole('meter', { name: /Profit Factor/i })).toBeInTheDocument();
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

  it('does not render Add to Strategy button when prop not provided', () => {
    render(<BacktestResultCard result={baseResult} />);
    expect(screen.queryByText(/\+ Strategy/)).not.toBeInTheDocument();
  });

  it('renders Add to Strategy button when status is done and prop is provided', () => {
    const doneResult: BacktestResponse = { ...baseResult, status: 'done' };
    const onAdd = vi.fn().mockResolvedValue(undefined);
    render(<BacktestResultCard result={doneResult} onAddToStrategy={onAdd} />);
    expect(screen.getByText(/\+ Strategy/)).toBeInTheDocument();
  });

  it('calls onAddToStrategy with strategy_name, params, and asset_id when clicked', async () => {
    const doneResult: BacktestResponse = {
      ...baseResult,
      status: 'done',
      strategy_params: { fast_window: 10, slow_window: 50 },
    };
    const onAdd = vi.fn().mockResolvedValue(undefined);
    render(<BacktestResultCard result={doneResult} onAddToStrategy={onAdd} />);
    fireEvent.click(screen.getByText(/\+ Strategy/));
    await waitFor(() =>
      expect(onAdd).toHaveBeenCalledWith('ma_crossover', { fast_window: 10, slow_window: 50 }, 1),
    );
  });

  it('renders indicator chart when indicator_series is provided', () => {
    const result: BacktestResponse = {
      ...baseResult,
      strategy_name: 'ema_cross',
      equity_curve: [
        { time: '2022-01-01', value: 100000 },
        { time: '2022-01-02', value: 101000 },
      ],
      indicator_series: [
        { time: '2022-01-01', fast_ema: 100.1, slow_ema: 99.8 },
        { time: '2022-01-02', fast_ema: 100.4, slow_ema: 99.9 },
      ],
    };
    render(<BacktestResultCard result={result} />);
    const charts = screen.getAllByTestId('area-chart');
    expect(charts.length).toBeGreaterThanOrEqual(2);
  });

  it('does not render indicator chart when indicator_series is absent', () => {
    const result: BacktestResponse = {
      ...baseResult,
      equity_curve: [{ time: '2022-01-01', value: 100000 }],
    };
    render(<BacktestResultCard result={result} />);
    const charts = screen.getAllByTestId('area-chart');
    expect(charts.length).toBe(1);
  });

  it('does not render indicator chart when indicator_series is empty', () => {
    const result: BacktestResponse = {
      ...baseResult,
      equity_curve: [{ time: '2022-01-01', value: 100000 }],
      indicator_series: [],
    };
    render(<BacktestResultCard result={result} />);
    const charts = screen.getAllByTestId('area-chart');
    expect(charts.length).toBe(1);
  });
});
