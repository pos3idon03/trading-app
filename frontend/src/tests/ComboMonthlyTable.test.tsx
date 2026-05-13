import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ComboMonthlyTable } from '../components/ComboMonthlyTable';
import type { ComboMonthlyRow } from '../api/types';

// ---------------------------------------------------------------------------
// Fixtures
// Represents 3 months using only Buy/Sell position states:
//   Jan: MA Cross in position (Buy), RSI out of position (Sell), combo: Sell
//   Feb: both in position (Buy), combo: Buy
//   Mar: MA Cross out (Sell), RSI in (Buy), combo: Sell
// ---------------------------------------------------------------------------

const strategies = ['ma_crossover', 'rsi'];

const sampleBreakdown: ComboMonthlyRow[] = [
  {
    month: '2022-01',
    combined_position: 'Sell',
    strategies: [
      {
        strategy_name: 'ma_crossover',
        position: 'Buy',
        indicators: { fast_ma: 148.23, slow_ma: 145.67 },
      },
      {
        strategy_name: 'rsi',
        position: 'Sell',
        indicators: { rsi: 42.30 },
      },
    ],
  },
  {
    month: '2022-02',
    combined_position: 'Buy',
    strategies: [
      {
        strategy_name: 'ma_crossover',
        position: 'Buy',
        indicators: { fast_ma: 152.10, slow_ma: 149.80 },
      },
      {
        strategy_name: 'rsi',
        position: 'Buy',
        indicators: { rsi: 55.10 },
      },
    ],
  },
  {
    month: '2022-03',
    combined_position: 'Sell',
    strategies: [
      {
        strategy_name: 'ma_crossover',
        position: 'Sell',
        indicators: { fast_ma: 147.00, slow_ma: 150.50 },
      },
      {
        strategy_name: 'rsi',
        position: 'Buy',
        indicators: { rsi: 35.00 },
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ComboMonthlyTable', () => {
  it('renders the correct number of month rows', () => {
    render(<ComboMonthlyTable breakdown={sampleBreakdown} strategies={strategies} />);
    expect(screen.getByText('Jan 2022')).toBeInTheDocument();
    expect(screen.getByText('Feb 2022')).toBeInTheDocument();
    expect(screen.getByText('Mar 2022')).toBeInTheDocument();
  });

  it('renders strategy column headers', () => {
    render(<ComboMonthlyTable breakdown={sampleBreakdown} strategies={strategies} />);
    expect(screen.getByText('MA Cross')).toBeInTheDocument();
    expect(screen.getByText('RSI')).toBeInTheDocument();
  });

  it('renders the Combined column header', () => {
    render(<ComboMonthlyTable breakdown={sampleBreakdown} strategies={strategies} />);
    expect(screen.getByText('Combined')).toBeInTheDocument();
  });

  it('shows Buy badge with green styling', () => {
    render(<ComboMonthlyTable breakdown={sampleBreakdown} strategies={strategies} />);
    const badges = screen.getAllByText('Buy');
    expect(badges.length).toBeGreaterThan(0);
    badges.forEach((badge) => {
      expect(badge).toHaveClass('text-emerald-400');
    });
  });

  it('shows Sell badge with red styling', () => {
    render(<ComboMonthlyTable breakdown={sampleBreakdown} strategies={strategies} />);
    const badges = screen.getAllByText('Sell');
    expect(badges.length).toBeGreaterThan(0);
    badges.forEach((badge) => {
      expect(badge).toHaveClass('text-red-400');
    });
  });

  it('never renders a Hold badge', () => {
    render(<ComboMonthlyTable breakdown={sampleBreakdown} strategies={strategies} />);
    expect(screen.queryByText('Hold')).toBeNull();
  });

  it('displays indicator values in cells', () => {
    render(<ComboMonthlyTable breakdown={sampleBreakdown} strategies={strategies} />);
    expect(screen.getByText('fast_ma: 148.23')).toBeInTheDocument();
    expect(screen.getByText('slow_ma: 145.67')).toBeInTheDocument();
    expect(screen.getByText('rsi: 42.30')).toBeInTheDocument();
  });

  it('displays combined_position for each row', () => {
    render(<ComboMonthlyTable breakdown={sampleBreakdown} strategies={strategies} />);
    const allBuyBadges = screen.getAllByText('Buy');
    expect(allBuyBadges.length).toBeGreaterThanOrEqual(1);
    const allSellBadges = screen.getAllByText('Sell');
    expect(allSellBadges.length).toBeGreaterThanOrEqual(1);
  });

  it('returns null when breakdown is empty', () => {
    const { container } = render(
      <ComboMonthlyTable breakdown={[]} strategies={strategies} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('uses the section heading', () => {
    render(<ComboMonthlyTable breakdown={sampleBreakdown} strategies={strategies} />);
    expect(screen.getByText('Monthly Strategy Breakdown')).toBeInTheDocument();
  });

  it('handles null indicator values gracefully', () => {
    const withNulls: ComboMonthlyRow[] = [
      {
        month: '2022-04',
        combined_position: 'Sell',
        strategies: [
          {
            strategy_name: 'ma_crossover',
            position: 'Sell',
            indicators: { fast_ma: null, slow_ma: null },
          },
          {
            strategy_name: 'rsi',
            position: 'Sell',
            indicators: { rsi: null },
          },
        ],
      },
    ];
    const { container } = render(
      <ComboMonthlyTable breakdown={withNulls} strategies={strategies} />
    );
    expect(container.querySelector('table')).toBeInTheDocument();
  });

  it('shows dash when a strategy is missing from a row', () => {
    const withMissing: ComboMonthlyRow[] = [
      {
        month: '2022-05',
        combined_position: 'Sell',
        strategies: [
          {
            strategy_name: 'rsi',
            position: 'Buy',
            indicators: { rsi: 50.0 },
          },
          // ma_crossover deliberately absent
        ],
      },
    ];
    render(<ComboMonthlyTable breakdown={withMissing} strategies={strategies} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });
});
