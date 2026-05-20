import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import McSimulationOptimizeResults from '../components/McSimulationOptimizeResults';
import type { McSimulationOptimizeResponse } from '../api/types';

vi.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Legend: () => null,
}));

const mockResult: McSimulationOptimizeResponse = {
  asset_id: 1,
  symbol: 'AAPL',
  status: 'done',
  optimize_metric: 'prob_positive_return',
  n_splits: 5,
  best_params: { num_paths: 1000, calibration_years: 10 },
  best_metric: 0.72,
  best_avg_oos_max_drawdown: -0.15,
  all_results: [
    {
      params: { num_paths: 1000, calibration_years: 10 },
      avg_oos_metric: 0.72,
      avg_oos_max_drawdown: -0.15,
    },
    {
      params: { num_paths: 500, calibration_years: 5 },
      avg_oos_metric: 0.55,
      avg_oos_max_drawdown: -0.2,
    },
  ],
  best_run_stats: {
    mean_terminal: 1.1,
    std_terminal: 0.05,
    p5: 1.0,
    p25: 1.05,
    p50: 1.1,
    p75: 1.15,
    p95: 1.2,
    prob_positive_return: 0.65,
    mean_max_drawdown: -0.1,
  },
  best_run_percentile_paths: { '50': [1.0, 1.05, 1.1] },
  duration_ms: 1200,
};

describe('McSimulationOptimizeResults', () => {
  it('renders best parameters', () => {
    render(<McSimulationOptimizeResults result={mockResult} />);
    expect(screen.getByText('Best Parameters')).toBeInTheDocument();
    expect(screen.getByText('num_paths')).toBeInTheDocument();
    expect(screen.getByText('1000')).toBeInTheDocument();
  });

  it('renders best-run simulation metrics', () => {
    render(<McSimulationOptimizeResults result={mockResult} />);
    expect(screen.getByText('Best-Run Simulation')).toBeInTheDocument();
    expect(screen.getByText('65.0%')).toBeInTheDocument();
  });

  it('renders all combinations table', () => {
    render(<McSimulationOptimizeResults result={mockResult} />);
    expect(screen.getByText(/All Parameter Combinations/)).toBeInTheDocument();
    expect(screen.getByText('calibration_years')).toBeInTheDocument();
  });

  it('renders percentile path chart when paths provided', () => {
    render(<McSimulationOptimizeResults result={mockResult} />);
    expect(screen.getByText('Best-Run Percentile Paths')).toBeInTheDocument();
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });
});
