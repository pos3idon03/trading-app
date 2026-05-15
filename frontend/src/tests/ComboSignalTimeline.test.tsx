import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ComboSignalTimeline } from '../components/ComboSignalTimeline';
import type { ComboStrategySignal } from '../api/types';

function makeStrategy(
  name: string,
  signals: { time: string; signal: 'Buy' | 'Neutral' | 'Sell' }[] = [],
): ComboStrategySignal {
  return {
    strategy_name: name,
    trade_log: [],
    indicator_series: [],
    equity_curve: [{ time: '2022-01-01', value: 100_000 }],
    signal_timeline: signals,
  };
}

// MA crossover: directional (Buy / Sell)
// RSI: neutral-aware (Buy / Neutral)
const TWO_STRATEGIES: ComboStrategySignal[] = [
  makeStrategy('ma_crossover', [
    { time: '2022-01-01', signal: 'Buy' },
    { time: '2022-02-01', signal: 'Sell' },
    { time: '2022-03-01', signal: 'Buy' },
  ]),
  makeStrategy('rsi', [
    { time: '2022-01-01', signal: 'Buy' },
    { time: '2022-02-01', signal: 'Neutral' },
    { time: '2022-03-01', signal: 'Neutral' },
  ]),
];

describe('ComboSignalTimeline', () => {
  it('renders nothing when strategies list is empty', () => {
    const { container } = render(<ComboSignalTimeline strategies={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the section heading', () => {
    render(<ComboSignalTimeline strategies={TWO_STRATEGIES} />);
    expect(screen.getByText(/Signal Agreement Timeline/i)).toBeInTheDocument();
  });

  it('renders descriptive subtitle text mentioning Neutral', () => {
    render(<ComboSignalTimeline strategies={TWO_STRATEGIES} />);
    expect(screen.getByText(/Neutral/i)).toBeInTheDocument();
  });

  it('renders chart elements for each provided strategy', () => {
    const { container } = render(<ComboSignalTimeline strategies={TWO_STRATEGIES} />);
    expect(container.querySelector('.recharts-responsive-container')).toBeTruthy();
    expect(screen.getByText(/Signal Agreement Timeline/i)).toBeInTheDocument();
  });

  it('shows all-Buy agreement banner when all strategies are Buy on last bar', () => {
    const allBuy: ComboStrategySignal[] = [
      makeStrategy('ma_crossover', [{ time: '2022-01-01', signal: 'Buy' }]),
      makeStrategy('rsi', [{ time: '2022-01-01', signal: 'Buy' }]),
    ];
    render(<ComboSignalTimeline strategies={allBuy} />);
    expect(screen.getByText(/All strategies agree: Buy/i)).toBeInTheDocument();
  });

  it('shows all-Sell agreement banner when all strategies are Sell on last bar', () => {
    const allSell: ComboStrategySignal[] = [
      makeStrategy('ma_crossover', [{ time: '2022-01-01', signal: 'Sell' }]),
      makeStrategy('macd', [{ time: '2022-01-01', signal: 'Sell' }]),
    ];
    render(<ComboSignalTimeline strategies={allSell} />);
    expect(screen.getByText(/All strategies agree: Sell/i)).toBeInTheDocument();
  });

  it('shows all-Neutral banner when all strategies are Neutral on last bar', () => {
    const allNeutral: ComboStrategySignal[] = [
      makeStrategy('rsi', [{ time: '2022-01-01', signal: 'Neutral' }]),
      makeStrategy('lrsi', [{ time: '2022-01-01', signal: 'Neutral' }]),
    ];
    render(<ComboSignalTimeline strategies={allNeutral} />);
    expect(screen.getByText(/All strategies are Neutral/i)).toBeInTheDocument();
  });

  it('does not show agreement banner when strategies disagree on last bar', () => {
    render(<ComboSignalTimeline strategies={TWO_STRATEGIES} />);
    expect(screen.queryByText(/All strategies agree/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/All strategies are Neutral/i)).not.toBeInTheDocument();
  });

  it('renders chart container element', () => {
    const { container } = render(<ComboSignalTimeline strategies={TWO_STRATEGIES} />);
    expect(container.querySelector('.recharts-responsive-container')).toBeTruthy();
  });

  it('handles a single strategy with Neutral signals without crashing', () => {
    const single = [
      makeStrategy('rsi', [
        { time: '2022-01-01', signal: 'Buy' },
        { time: '2022-02-01', signal: 'Neutral' },
      ]),
    ];
    render(<ComboSignalTimeline strategies={single} />);
    expect(screen.getByText(/Signal Agreement Timeline/i)).toBeInTheDocument();
  });

  it('accepts syncId prop without crashing', () => {
    render(<ComboSignalTimeline strategies={TWO_STRATEGIES} syncId="test-sync" />);
    expect(screen.getByText(/Signal Agreement Timeline/i)).toBeInTheDocument();
  });
});
