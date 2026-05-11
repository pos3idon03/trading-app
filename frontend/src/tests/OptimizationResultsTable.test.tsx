import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import OptimizationResultsTable from '../components/OptimizationResultsTable';
import type { OptimizationSummary } from '../api/types';

const results: OptimizationSummary[] = [
  { params: { fast_window: 10, slow_window: 50 }, avg_oos_metric: 1.2 },
  { params: { fast_window: 20, slow_window: 100 }, avg_oos_metric: 0.8 },
  { params: { fast_window: 5, slow_window: 30 }, avg_oos_metric: 1.5 },
];

describe('OptimizationResultsTable', () => {
  it('renders a row for each result', () => {
    render(<OptimizationResultsTable results={results} metric="sharpe_ratio" />);
    const rows = screen.getAllByRole('row');
    expect(rows.length).toBe(results.length + 1);
  });

  it('renders parameter column headers', () => {
    render(<OptimizationResultsTable results={results} metric="sharpe_ratio" />);
    expect(screen.getByText('fast_window')).toBeInTheDocument();
    expect(screen.getByText('slow_window')).toBeInTheDocument();
  });

  it('shows the metric column header', () => {
    render(<OptimizationResultsTable results={results} metric="sharpe_ratio" />);
    expect(screen.getByText(/Avg OOS sharpe_ratio/)).toBeInTheDocument();
  });

  it('sorts results descending by avg_oos_metric', () => {
    render(<OptimizationResultsTable results={results} metric="sharpe_ratio" />);
    const cells = screen.getAllByRole('cell');
    const metricCells = cells.filter((c) => /^[0-9]+\.[0-9]+$/.test(c.textContent?.trim() ?? ''));
    const values = metricCells.map((c) => parseFloat(c.textContent ?? '0'));
    for (let i = 0; i < values.length - 1; i++) {
      expect(values[i]).toBeGreaterThanOrEqual(values[i + 1]);
    }
  });

  it('handles Infinity values gracefully', () => {
    const infinityResults: OptimizationSummary[] = [
      { params: { x: 1 }, avg_oos_metric: Infinity },
    ];
    render(<OptimizationResultsTable results={infinityResults} metric="sharpe_ratio" />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });
});
