import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import BacktestEquityCurve, { computeEquityYDomain } from '../components/BacktestEquityCurve';
import type { TradeRecord } from '../api/types';

vi.mock('recharts', () => ({
  ComposedChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="composed-chart">{children}</div>
  ),
  Area: ({ dataKey }: { dataKey: string }) => <div data-testid={`area-${dataKey}`} />,
  Line: ({ dataKey, stroke }: { dataKey: string; stroke: string }) => (
    <div data-testid={`line-${dataKey}`} data-stroke={stroke} />
  ),
  XAxis: () => null,
  YAxis: ({ domain }: { domain?: [number, number] }) => (
    <div data-testid="y-axis" data-domain={domain?.join(',') ?? ''} />
  ),
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
  ReferenceDot: ({ x, shape }: { x: string; shape: React.ReactElement }) => (
    <div data-testid="reference-dot" data-x={x}>{shape}</div>
  ),
  Legend: () => null,
}));

const equityCurve = [
  { time: '2022-01-03 00:00:00', value: 100000 },
  { time: '2022-01-04 00:00:00', value: 101000 },
  { time: '2022-01-05 00:00:00', value: 102000 },
];

const buyHoldCurve = [
  { time: '2022-01-03 00:00:00', value: 100000 },
  { time: '2022-01-04 00:00:00', value: 100500 },
  { time: '2022-01-05 00:00:00', value: 101000 },
];

const tradeLog: TradeRecord[] = [
  {
    entry_time: '2022-01-03 00:00:00',
    exit_time: '2022-01-05 00:00:00',
    direction: 'long',
    entry_price: 100,
    exit_price: 102,
    pnl: 200,
    return_pct: 0.02,
  },
];

describe('BacktestEquityCurve', () => {
  it('renders the composed chart', () => {
    render(
      <BacktestEquityCurve data={equityCurve} gradientId="grad-1" />,
    );
    expect(screen.getByTestId('composed-chart')).toBeInTheDocument();
  });

  it('renders the strategy area', () => {
    render(
      <BacktestEquityCurve data={equityCurve} gradientId="grad-1" />,
    );
    expect(screen.getByTestId('area-value')).toBeInTheDocument();
  });

  it('renders the buy-and-hold line in purple when buyHoldData is provided', () => {
    render(
      <BacktestEquityCurve
        data={equityCurve}
        gradientId="grad-1"
        buyHoldData={buyHoldCurve}
      />,
    );
    const line = screen.getByTestId('line-buyHold');
    expect(line).toBeInTheDocument();
    expect(line).toHaveAttribute('data-stroke', '#a855f7');
  });

  it('does not render buy-and-hold line when no buyHoldData', () => {
    render(
      <BacktestEquityCurve data={equityCurve} gradientId="grad-1" />,
    );
    expect(screen.queryByTestId('line-buyHold')).not.toBeInTheDocument();
  });

  it('renders reference dots for each trade entry and exit', () => {
    render(
      <BacktestEquityCurve
        data={equityCurve}
        gradientId="grad-1"
        tradeLog={tradeLog}
      />,
    );
    const dots = screen.getAllByTestId('reference-dot');
    expect(dots.length).toBe(2);
  });

  it('matches trade timestamps to equity curve time strings for ReferenceDot x', () => {
    const isoTrades: TradeRecord[] = [
      {
        entry_time: '2022-01-03T00:00:00.000000000',
        exit_time: '2022-01-05T00:00:00.000000000',
        direction: 'long',
        entry_price: 100,
        exit_price: 102,
        pnl: 200,
        return_pct: 0.02,
      },
    ];
    render(
      <BacktestEquityCurve data={equityCurve} gradientId="grad-1" tradeLog={isoTrades} />,
    );
    const dots = screen.getAllByTestId('reference-dot');
    expect(dots[0]).toHaveAttribute('data-x', '2022-01-03 00:00:00');
    expect(dots[1]).toHaveAttribute('data-x', '2022-01-05 00:00:00');
  });

  it('renders no reference dots when tradeLog is empty', () => {
    render(
      <BacktestEquityCurve data={equityCurve} gradientId="grad-1" tradeLog={[]} />,
    );
    expect(screen.queryByTestId('reference-dot')).not.toBeInTheDocument();
  });

  it('renders legend items for strategy and buy & hold', () => {
    render(
      <BacktestEquityCurve
        data={equityCurve}
        gradientId="grad-1"
        buyHoldData={buyHoldCurve}
      />,
    );
    expect(screen.getByText('Strategy')).toBeInTheDocument();
    expect(screen.getByText('Buy & Hold')).toBeInTheDocument();
    expect(screen.getByText('Buy')).toBeInTheDocument();
    expect(screen.getByText('Sell')).toBeInTheDocument();
  });

  it('uses compact height prop correctly', () => {
    const { container } = render(
      <BacktestEquityCurve data={equityCurve} gradientId="grad-1" compact />,
    );
    expect(container).toBeInTheDocument();
  });

  it('renders reference dots from executionLog when provided', () => {
    render(
      <BacktestEquityCurve
        data={equityCurve}
        gradientId="grad-1"
        executionLog={[
          { time: '2022-01-03 00:00:00', side: 'buy', price: 100, equity: 100000 },
          { time: '2022-01-05 00:00:00', side: 'sell', price: 102, equity: 102000 },
        ]}
      />,
    );
    const dots = screen.getAllByTestId('reference-dot');
    expect(dots.length).toBe(2);
  });

  it('skips outer card wrapper when bare is true', () => {
    const { container } = render(
      <BacktestEquityCurve data={equityCurve} gradientId="grad-1" bare />,
    );
    expect(container.querySelector('.card')).not.toBeInTheDocument();
  });

  it('sets y-axis domain rounded to nearest $100 from equity data', () => {
    render(
      <BacktestEquityCurve
        data={[
          { time: '2024-01-01', value: 1034 },
          { time: '2024-01-02', value: 1187 },
        ]}
        gradientId="grad-domain"
      />,
    );
    expect(screen.getByTestId('y-axis').getAttribute('data-domain')).toBe('1000,1200');
  });
});

describe('computeEquityYDomain', () => {
  it('rounds min down and max up to nearest $100', () => {
    expect(computeEquityYDomain([1034, 1187])).toEqual([1000, 1200]);
  });

  it('pads flat lines by ±$100', () => {
    expect(computeEquityYDomain([1000, 1000])).toEqual([900, 1100]);
  });

  it('includes buy-and-hold values in domain', () => {
    expect(computeEquityYDomain([1050, 1100, 980])).toEqual([900, 1200]);
  });
});
