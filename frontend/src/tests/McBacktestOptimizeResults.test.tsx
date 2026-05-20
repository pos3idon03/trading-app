import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import McBacktestOptimizeResults from '../components/McBacktestOptimizeResults';
import type { McBacktestOptimizeResponse } from '../api/types';

const mockResult: McBacktestOptimizeResponse = {
  asset_id: 1,
  symbol: 'AAPL',
  status: 'done',
  optimize_metric: 'sharpe_ratio',
  n_splits: 5,
  best_params: {
    buy_threshold: 0.52,
    sell_threshold: 0.48,
    num_paths: 500,
    calibration_years: 10,
  },
  best_metric: 1.2,
  best_avg_oos_max_drawdown: -0.08,
  all_results: [
    {
      params: { buy_threshold: 0.52, sell_threshold: 0.48, num_paths: 500, calibration_years: 10 },
      avg_oos_metric: 1.2,
      avg_oos_max_drawdown: -0.08,
    },
  ],
  full_period_metrics: {
    total_return: 0.15,
    sharpe_ratio: 1.1,
    sortino_ratio: 1.3,
    max_drawdown: -0.1,
    win_rate: 0.6,
    profit_factor: 1.5,
    num_trades: 5,
  },
  duration_ms: 800,
};

describe('McBacktestOptimizeResults', () => {
  it('renders best backtest parameters with formatted thresholds', () => {
    render(<McBacktestOptimizeResults result={mockResult} />);
    expect(screen.getByText('Best Backtest Parameters')).toBeInTheDocument();
    expect(screen.getByText('52%')).toBeInTheDocument();
  });

  it('calls onApply when apply button clicked', () => {
    const onApply = vi.fn();
    render(<McBacktestOptimizeResults result={mockResult} onApply={onApply} />);
    fireEvent.click(screen.getByText('Apply to Backtest Tab'));
    expect(onApply).toHaveBeenCalledTimes(1);
  });

  it('renders top combos table', () => {
    render(<McBacktestOptimizeResults result={mockResult} />);
    expect(screen.getByText(/Top 10 Parameter Combinations/)).toBeInTheDocument();
  });

  it('renders hold-out metrics when present', () => {
    const withHoldout: McBacktestOptimizeResponse = {
      ...mockResult,
      holdout_metrics: {
        total_return: 0.08,
        sharpe_ratio: 1.0,
        sortino_ratio: 1.2,
        max_drawdown: -0.05,
        win_rate: 0.55,
        profit_factor: 1.3,
        num_trades: 4,
      },
    };
    render(<McBacktestOptimizeResults result={withHoldout} />);
    expect(screen.getByText('Hold-out Period (last 20%)')).toBeInTheDocument();
  });
});
