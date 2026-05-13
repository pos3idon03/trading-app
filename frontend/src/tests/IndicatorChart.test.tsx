import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import IndicatorChart from '../components/IndicatorChart';

vi.mock('recharts', () => ({
  ComposedChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="indicator-composed-chart">{children}</div>
  ),
  Line: ({ dataKey }: { dataKey: string }) => <div data-testid={`line-${dataKey}`} />,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
  ReferenceLine: ({ y }: { y: number }) => <div data-testid={`ref-line-${y}`} />,
}));

const makeRows = (keys: string[], n = 30) =>
  Array.from({ length: n }, (_, i) => ({
    time: `2022-01-${String(i + 1).padStart(2, '0')}`,
    ...Object.fromEntries(keys.map((k) => [k, Math.random() * 100])),
  }));

describe('IndicatorChart', () => {
  it('renders nothing when data is empty', () => {
    const { container } = render(
      <IndicatorChart data={[]} strategyName="ema_cross" />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when rows have no indicator keys', () => {
    const { container } = render(
      <IndicatorChart data={[{ time: '2022-01-01' }]} strategyName="ema_cross" />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders chart for ema_cross with fast and slow lines', () => {
    const data = makeRows(['fast_ema', 'slow_ema']);
    render(<IndicatorChart data={data} strategyName="ema_cross" />);
    expect(screen.getByTestId('indicator-composed-chart')).toBeInTheDocument();
    expect(screen.getByTestId('line-fast_ema')).toBeInTheDocument();
    expect(screen.getByTestId('line-slow_ema')).toBeInTheDocument();
  });

  it('renders chart for rsi with reference lines at 70 and 30', () => {
    const data = makeRows(['rsi']);
    render(<IndicatorChart data={data} strategyName="rsi" />);
    expect(screen.getByTestId('line-rsi')).toBeInTheDocument();
    expect(screen.getByTestId('ref-line-70')).toBeInTheDocument();
    expect(screen.getByTestId('ref-line-30')).toBeInTheDocument();
  });

  it('uses param-overridden reference lines for rsi when params provided', () => {
    const data = makeRows(['rsi']);
    render(
      <IndicatorChart
        data={data}
        strategyName="rsi"
        strategyParams={{ overbought: 75, oversold: 25 }}
      />,
    );
    expect(screen.getByTestId('ref-line-75')).toBeInTheDocument();
    expect(screen.getByTestId('ref-line-25')).toBeInTheDocument();
  });

  it('renders chart for macd with zero reference line', () => {
    const data = makeRows(['macd', 'signal']);
    render(<IndicatorChart data={data} strategyName="macd" />);
    expect(screen.getByTestId('line-macd')).toBeInTheDocument();
    expect(screen.getByTestId('line-signal')).toBeInTheDocument();
    expect(screen.getByTestId('ref-line-0')).toBeInTheDocument();
  });

  it('renders chart for aroon with up and down lines', () => {
    const data = makeRows(['aroon_up', 'aroon_down']);
    render(<IndicatorChart data={data} strategyName="aroon" />);
    expect(screen.getByTestId('line-aroon_up')).toBeInTheDocument();
    expect(screen.getByTestId('line-aroon_down')).toBeInTheDocument();
  });

  it('renders chart for stoch_rsi with %K and %D lines', () => {
    const data = makeRows(['stoch_k', 'stoch_d']);
    render(<IndicatorChart data={data} strategyName="stoch_rsi" />);
    expect(screen.getByTestId('line-stoch_k')).toBeInTheDocument();
    expect(screen.getByTestId('line-stoch_d')).toBeInTheDocument();
  });

  it('renders title label for known strategy', () => {
    const data = makeRows(['fast_ema', 'slow_ema']);
    render(<IndicatorChart data={data} strategyName="ema_cross" />);
    expect(screen.getByText('EMA Lines')).toBeInTheDocument();
  });

  it('renders fallback chart for unknown strategy key', () => {
    const data = makeRows(['some_indicator']);
    render(<IndicatorChart data={data} strategyName="unknown_strategy" />);
    expect(screen.getByTestId('indicator-composed-chart')).toBeInTheDocument();
    expect(screen.getByTestId('line-some_indicator')).toBeInTheDocument();
  });

  it('renders chart for breakout with all four band lines', () => {
    const data = makeRows(['bb_upper', 'bb_lower', 'donchian_high', 'donchian_low']);
    render(<IndicatorChart data={data} strategyName="breakout" />);
    expect(screen.getByTestId('line-bb_upper')).toBeInTheDocument();
    expect(screen.getByTestId('line-bb_lower')).toBeInTheDocument();
    expect(screen.getByTestId('line-donchian_high')).toBeInTheDocument();
    expect(screen.getByTestId('line-donchian_low')).toBeInTheDocument();
  });

  it('renders chart for mean_reversion with z_score and reference lines', () => {
    const data = makeRows(['z_score']);
    render(
      <IndicatorChart
        data={data}
        strategyName="mean_reversion"
        strategyParams={{ z_threshold: 2.0 }}
      />,
    );
    expect(screen.getByTestId('line-z_score')).toBeInTheDocument();
    expect(screen.getByTestId('ref-line-2')).toBeInTheDocument();
    expect(screen.getByTestId('ref-line--2')).toBeInTheDocument();
  });
});
