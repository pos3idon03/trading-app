import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import McProbPositiveChart, { buildChartData, computeYDomain } from '../components/McProbPositiveChart';
import type { McBacktestSignalPoint } from '../api/types';

vi.mock('recharts', () => ({
  ComposedChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="composed-chart">{children}</div>
  ),
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
  ReferenceLine: ({ y, label }: { y: number; label?: { value?: string } }) => (
    <div data-testid="reference-line" data-y={y} data-label={label?.value ?? ''} />
  ),
}));

const sampleSignalLog: McBacktestSignalPoint[] = [
  { time: '2024-01-01T00:00:00+00:00', prob_positive: 0.52, signal: 'hold' },
  { time: '2024-01-02T00:00:00+00:00', prob_positive: 0.68, signal: 'buy' },
  { time: '2024-01-03T00:00:00+00:00', prob_positive: null, signal: 'hold' },
];

describe('McProbPositiveChart', () => {
  it('renders title Prob. Positive Return', () => {
    render(
      <McProbPositiveChart
        signalLog={sampleSignalLog}
        buyThreshold={0.65}
        sellThreshold={0.4}
      />,
    );
    expect(screen.getByText('Prob. Positive Return')).toBeInTheDocument();
  });

  it('renders chart with sample signal log', () => {
    render(
      <McProbPositiveChart
        signalLog={sampleSignalLog}
        buyThreshold={0.65}
        sellThreshold={0.4}
      />,
    );
    expect(screen.getByTestId('composed-chart')).toBeInTheDocument();
    expect(screen.getByTestId('line-probPct')).toBeInTheDocument();
  });

  it('returns null when signal log is empty', () => {
    const { container } = render(
      <McProbPositiveChart
        signalLog={[]}
        buyThreshold={0.65}
        sellThreshold={0.4}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null when all probabilities are null', () => {
    const nullLog: McBacktestSignalPoint[] = [
      { time: '2024-01-01T00:00:00+00:00', prob_positive: null, signal: 'hold' },
    ];
    const { container } = render(
      <McProbPositiveChart
        signalLog={nullLog}
        buyThreshold={0.65}
        sellThreshold={0.4}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders reference line labels with threshold percentages', () => {
    render(
      <McProbPositiveChart
        signalLog={sampleSignalLog}
        buyThreshold={0.65}
        sellThreshold={0.4}
      />,
    );
    const labels = screen.getAllByTestId('reference-line').map((el) => el.getAttribute('data-label'));
    expect(labels).toContain('Buy 65%');
    expect(labels).toContain('Sell 40%');
    expect(labels).not.toContain('Hold 50%');
  });

  it('uses dynamic y-axis domain rounded to nearest dozen', () => {
    const tightLog: McBacktestSignalPoint[] = [
      { time: '2024-01-01T00:00:00+00:00', prob_positive: 0.48, signal: 'hold' },
      { time: '2024-01-02T00:00:00+00:00', prob_positive: 0.53, signal: 'hold' },
    ];
    render(
      <McProbPositiveChart
        signalLog={tightLog}
        buyThreshold={0.54}
        sellThreshold={0.47}
      />,
    );
    expect(screen.getByTestId('y-axis').getAttribute('data-domain')).toBe('40,60');
  });

  it('maps blended diagnostics in chart data', () => {
    const blendedLog: McBacktestSignalPoint[] = [
      {
        time: '2024-01-01T00:00:00+00:00',
        prob_positive: 0.55,
        prob_trend: 0.62,
        prob_reversion: 0.48,
        regime_weight: 0.5,
        signal: 'hold',
      },
    ];
    const data = buildChartData(blendedLog);
    expect(data[0].probPct).toBe(55);
    expect(data[0].probTrendPct).toBe(62);
    expect(data[0].probReversionPct).toBe(48);
    expect(data[0].regimeWeightPct).toBe(50);
  });
});

describe('computeYDomain', () => {
  it('floors min and ceils max to nearest dozen including thresholds', () => {
    const data = [
      { time: 't1', probPct: 48, probTrendPct: null, probReversionPct: null, regimeWeightPct: null },
      { time: 't2', probPct: 53, probTrendPct: null, probReversionPct: null, regimeWeightPct: null },
    ];
    expect(computeYDomain(data, 54, 47)).toEqual([40, 60]);
  });

  it('clamps domain within 0-100', () => {
    const data = [
      { time: 't1', probPct: 2, probTrendPct: null, probReversionPct: null, regimeWeightPct: null },
      { time: 't2', probPct: 8, probTrendPct: null, probReversionPct: null, regimeWeightPct: null },
    ];
    expect(computeYDomain(data, 5, 5)).toEqual([0, 10]);
  });
});
