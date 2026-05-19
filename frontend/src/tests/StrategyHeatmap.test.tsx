import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StrategyHeatmap from '../components/StrategyHeatmap';

describe('StrategyHeatmap', () => {
  const strategies = ['ma_crossover', 'rsi'];
  const values: (number | null)[][] = [
    [1.5, 0.8],
    [0.8, 1.2],
  ];

  it('renders grid with strategy labels', () => {
    render(
      <StrategyHeatmap
        strategies={strategies}
        values={values}
        metric="sharpe_ratio"
        combinationMode="majority"
      />,
    );
    expect(screen.getByRole('grid', { name: /strategy combination heatmap/i })).toBeInTheDocument();
    expect(screen.getByText(/Strategy combination heatmap/i)).toBeInTheDocument();
  });

  it('formats sharpe ratio cells', () => {
    render(
      <StrategyHeatmap
        strategies={strategies}
        values={values}
        metric="sharpe_ratio"
        combinationMode="majority"
      />,
    );
    expect(screen.getAllByText('1.50').length).toBeGreaterThan(0);
    expect(screen.getAllByText('0.80').length).toBeGreaterThan(0);
  });

  it('renders em dash for null values', () => {
    const nullValues: (number | null)[][] = [
      [null, 0.5],
      [0.5, null],
    ];
    render(
      <StrategyHeatmap
        strategies={strategies}
        values={nullValues}
        metric="total_return"
        combinationMode="and"
      />,
    );
    expect(screen.getAllByText('—').length).toBe(2);
  });

  it('shows combination mode in header', () => {
    render(
      <StrategyHeatmap
        strategies={strategies}
        values={values}
        metric="profit_factor"
        combinationMode="weighted"
      />,
    );
    expect(screen.getByText(/Mode: weighted/i)).toBeInTheDocument();
  });
});
