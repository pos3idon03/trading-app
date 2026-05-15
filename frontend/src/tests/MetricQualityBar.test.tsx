import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import MetricQualityBar from '../components/MetricQualityBar';

describe('MetricQualityBar', () => {
  it('renders meter with formatted value and tier for sharpe', () => {
    render(
      <MetricQualityBar
        label="Sharpe Ratio"
        value={1.5}
        formattedValue="1.500"
        kind="sharpe"
      />,
    );
    expect(screen.getByText('Sharpe Ratio')).toBeInTheDocument();
    expect(screen.getByText('1.500')).toBeInTheDocument();
    const meter = screen.getByRole('meter', { name: /Sharpe Ratio.*Good/i });
    expect(meter).toHaveAttribute('aria-valuenow', '43');
    expect(meter).toHaveAttribute('title', 'Good');
  });

  it('renders em dash when value is missing', () => {
    render(
      <MetricQualityBar
        label="Profit Factor"
        value={null}
        formattedValue="—"
        kind="profit_factor"
      />,
    );
    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.getByRole('meter', { name: /no data/i })).not.toHaveAttribute('aria-valuenow');
  });
});
