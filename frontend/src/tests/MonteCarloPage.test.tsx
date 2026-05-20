import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MonteCarloPage from '../pages/MonteCarloPage';

const mockRunBacktest = vi.fn();
const mockOptimizeBacktest = vi.fn();
const mockGetOptimizeBacktestJob = vi.fn();

vi.mock('../api/endpoints', () => ({
  dataApi: {
    getAssets: vi.fn().mockResolvedValue({
      assets: [
        {
          id: 1,
          symbol: 'AAPL',
          name: 'Apple Inc.',
          asset_type: 'stock',
          exchange: 'NASDAQ',
          currency: 'USD',
          is_active: true,
        },
      ],
    }),
  },
  simulationApi: {
    run: vi.fn().mockResolvedValue({
      simulation_id: 1,
      asset_id: 1,
      status: 'done',
      params: {},
      stats: {
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
      percentile_paths: { '50': [1, 1.1] },
      duration_ms: 100,
    }),
    runBacktest: (...args: unknown[]) => mockRunBacktest(...args),
    optimizeBacktest: (...args: unknown[]) => mockOptimizeBacktest(...args),
    getOptimizeBacktestJob: (...args: unknown[]) => mockGetOptimizeBacktestJob(...args),
  },
}));

vi.mock('recharts', () => ({
  ComposedChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Area: () => null,
  Line: () => null,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
  ReferenceDot: () => null,
  ReferenceLine: () => null,
  Legend: () => null,
}));

describe('MonteCarloPage — tabs and backtest', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockOptimizeBacktest.mockResolvedValue({ job_id: 1, status: 'pending' });
    mockGetOptimizeBacktestJob.mockResolvedValue({
      job_id: 1,
      asset_id: 1,
      symbol: 'AAPL',
      status: 'done',
      optimize_metric: 'sharpe_ratio',
      n_splits: 5,
      progress_pct: 100,
      completed_steps: 10,
      total_steps: 10,
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
          params: {
            buy_threshold: 0.52,
            sell_threshold: 0.48,
            num_paths: 500,
            calibration_years: 10,
          },
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
    });
    mockRunBacktest.mockResolvedValue({
      asset_id: 1,
      symbol: 'AAPL',
      status: 'done',
      metrics: {
        total_return: 0.12,
        sharpe_ratio: 1.1,
        sortino_ratio: 1.3,
        max_drawdown: -0.08,
        win_rate: 0.55,
        profit_factor: 1.4,
        num_trades: 3,
      },
      equity_curve: [{ time: '2024-01-01', value: 1000 }],
      buy_hold_curve: [{ time: '2024-01-01', value: 1000 }],
      signal_log: [
        { time: '2024-01-01T00:00:00+00:00', prob_positive: 0.55, effective_prob: 0.55, signal: 'FLAT' },
        { time: '2024-01-02T00:00:00+00:00', prob_positive: 0.72, effective_prob: 0.72, signal: 'BUY' },
      ],
      zone_stats: {
        entry_zone_pct: 50,
        exit_zone_pct: 0,
        middle_zone_pct: 50,
        bars_with_prob: 12,
        prob_min: 0.44,
        prob_p25: 0.46,
        prob_median: 0.5,
        prob_p75: 0.54,
        prob_max: 0.56,
        suggested_buy_threshold: 0.54,
        suggested_sell_threshold: 0.46,
      },
      trade_log: [],
      bars_evaluated: 50,
      duration_ms: 200,
    });
  });

  it('renders Simulation, Backtest, and Optimize tabs', async () => {
    render(<MonteCarloPage />);
    expect(screen.getByRole('button', { name: 'Simulation' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Backtest' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Optimize' })).toBeInTheDocument();
  });

  it('shows simulation form by default', async () => {
    render(<MonteCarloPage />);
    await waitFor(() => expect(screen.getByText('Run Simulation')).toBeInTheDocument());
  });

  it('switches to backtest tab and shows threshold fields', async () => {
    render(<MonteCarloPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Backtest' }));
    await waitFor(() => expect(screen.getByText('Run Backtest')).toBeInTheDocument());
    expect(screen.getByLabelText(/entry %/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/exit %/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/hold %/i)).not.toBeInTheDocument();
  });

  it('calls runBacktest with converted thresholds on submit', async () => {
    render(<MonteCarloPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Backtest' }));
    await waitFor(() => expect(screen.getByText('Run Backtest')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Run Backtest'));
    await waitFor(() => expect(mockRunBacktest).toHaveBeenCalledTimes(1));
    const payload = mockRunBacktest.mock.calls[0][0];
    expect(payload.symbol).toBe('AAPL');
    expect(payload.buy_threshold).toBe(0.65);
    expect(payload.sell_threshold).toBe(0.4);
    expect(payload.hold_threshold).toBeUndefined();
    expect(payload.initial_capital).toBe(1000);
    expect(payload.num_paths).toBe(500);
    await waitFor(() => expect(screen.getByText('Prob. Positive Return')).toBeInTheDocument());
  });

  it('shows suggested thresholds and applies them to form fields', async () => {
    render(<MonteCarloPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Backtest' }));
    await waitFor(() => expect(screen.getByText('Run Backtest')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Run Backtest'));
    await waitFor(() => expect(screen.getByText(/Suggested entry ≥ 54.0%/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /apply suggested thresholds/i }));
    expect(screen.getByDisplayValue('54')).toBeInTheDocument();
    expect(screen.getByDisplayValue('46')).toBeInTheDocument();
  });

  it('preserves simulation tab content when switching back', async () => {
    render(<MonteCarloPage />);
    await waitFor(() => expect(screen.getByText('Run Simulation')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: 'Backtest' }));
    await waitFor(() => expect(screen.getByText('Run Backtest')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: 'Simulation' }));
    expect(screen.getByText('Run Simulation')).toBeInTheDocument();
  });

  it('renders trade table when backtest returns open position row', async () => {
    mockRunBacktest.mockResolvedValue({
      asset_id: 1,
      symbol: 'AMD',
      status: 'done',
      metrics: {
        total_return: 1.056,
        sharpe_ratio: 2.49,
        sortino_ratio: 3.15,
        max_drawdown: -0.2647,
        win_rate: 0,
        profit_factor: 0,
        num_trades: 0,
      },
      equity_curve: [
        { time: '2026-01-02T00:00:00+00:00', value: 1000 },
        { time: '2026-01-03T00:00:00+00:00', value: 1100 },
      ],
      buy_hold_curve: [
        { time: '2026-01-02T00:00:00+00:00', value: 1000 },
        { time: '2026-01-03T00:00:00+00:00', value: 1100 },
      ],
      execution_log: [
        { time: '2026-01-02T00:00:00+00:00', side: 'buy', price: 100, equity: 1000 },
      ],
      trade_log: [
        {
          entry_time: '2026-01-02T00:00:00+00:00',
          exit_time: null,
          direction: 'long',
          entry_price: 100,
          exit_price: null,
          pnl: 50,
          return_pct: 0.05,
        },
      ],
      bars_evaluated: 138,
      duration_ms: 223,
    });

    render(<MonteCarloPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Backtest' }));
    await waitFor(() => expect(screen.getByText('Run Backtest')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Run Backtest'));

    await waitFor(() => expect(screen.getByText('Buy Price')).toBeInTheDocument());
    expect(screen.getByText('Sell Date')).toBeInTheDocument();
    expect(screen.getByText('Open')).toBeInTheDocument();
    expect(screen.getByText('Total Transactions')).toBeInTheDocument();
  });

  it('calls backtest optimize and shows apply button', async () => {
    render(<MonteCarloPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Optimize' }));
    await waitFor(() => expect(screen.getByText('Run Optimization')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Run Optimization'));
    await waitFor(() => expect(mockOptimizeBacktest).toHaveBeenCalledTimes(1));
    const payload = mockOptimizeBacktest.mock.calls[0][0];
    expect(payload.symbol).toBe('AAPL');
    expect(payload.optimize_metric).toBe('sharpe_ratio');
    expect(payload.param_grid.buy_threshold).toEqual([52, 55, 58]);
    await waitFor(() => expect(screen.getByText('Best Backtest Parameters')).toBeInTheDocument());
    expect(screen.getByText('Apply to Backtest Tab')).toBeInTheDocument();
  });

  it('applies optimize preset to backtest tab fields', async () => {
    render(<MonteCarloPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Optimize' }));
    await waitFor(() => expect(screen.getByText('Run Optimization')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Run Optimization'));
    await waitFor(() => expect(screen.getByText('Apply to Backtest Tab')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Apply to Backtest Tab'));
    await waitFor(() => expect(screen.getByText('Run Backtest')).toBeInTheDocument());
    expect(screen.getByLabelText(/entry %/i)).toHaveValue('52');
    expect(screen.getByLabelText(/exit %/i)).toHaveValue('48');
  });

  it('lists all MC model options in backtest tab', async () => {
    render(<MonteCarloPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Backtest' }));
    await waitFor(() => expect(screen.getByText('Run Backtest')).toBeInTheDocument());
    const modelSelect = screen.getAllByRole('combobox').find((el) => {
      const options = el.querySelectorAll('option');
      return Array.from(options).some((o) => o.textContent === 'Blended (ADX)');
    });
    expect(modelSelect).toBeTruthy();
    expect(modelSelect?.querySelector('option[value="ou_deviation"]')).toBeTruthy();
  });

  it('renders algo combo section and includes combo fields in payload when enabled', async () => {
    render(<MonteCarloPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Backtest' }));
    await waitFor(() => expect(screen.getByText('Run Backtest')).toBeInTheDocument());
    expect(screen.getByLabelText('Algo combo')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Algo combo'));
    const addSelect = screen.getByLabelText('Add algo strategy');
    fireEvent.change(addSelect, { target: { value: 'rsi' } });
    fireEvent.click(screen.getByText('Run Backtest'));
    await waitFor(() => expect(mockRunBacktest).toHaveBeenCalled());
    const payload = mockRunBacktest.mock.calls.at(-1)?.[0];
    expect(payload.combo_enabled).toBe(true);
    expect(payload.algo_strategies).toHaveLength(1);
    expect(payload.algo_strategies[0].strategy_name).toBe('rsi');
  });
});
