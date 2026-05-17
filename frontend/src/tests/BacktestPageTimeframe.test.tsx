import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BacktestPage from '../pages/BacktestPage';

// Stub API calls so the component mounts without network access.
vi.mock('../api/endpoints', () => ({
  dataApi: {
    getAssets: vi.fn().mockResolvedValue({
      assets: [{ id: 1, symbol: 'AAPL', name: 'Apple Inc.', is_active: true }],
    }),
  },
  backtestApi: {
    run: vi.fn().mockResolvedValue({
      asset_id: 1,
      strategy_name: 'ma_crossover',
      strategy_params: {},
      status: 'done',
      duration_ms: 50,
    }),
    optimize: vi.fn().mockResolvedValue({
      asset_id: 1,
      strategy_name: 'ma_crossover',
      status: 'done',
      optimize_metric: 'sharpe_ratio',
      n_splits: 5,
    }),
  },
}));

vi.mock('recharts', () => ({
  ComposedChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Area: () => null,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
  ReferenceDot: () => null,
  Legend: () => null,
}));

import { backtestApi } from '../api/endpoints';

describe('BacktestPage — Price Frequency selector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the Price Frequency label', async () => {
    render(<BacktestPage />);
    await waitFor(() => expect(screen.getByLabelText(/price frequency/i)).toBeInTheDocument());
  });

  it('defaults to Daily', async () => {
    render(<BacktestPage />);
    const select = await screen.findByLabelText<HTMLSelectElement>(/price frequency/i);
    expect(select.value).toBe('1d');
  });

  it('defaults start/end dates to today minus 3 years and today', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-15T12:00:00'));
    render(<BacktestPage />);
    const startInput = await screen.findByLabelText<HTMLInputElement>(/start date/i);
    const endInput = screen.getByLabelText<HTMLInputElement>(/end date/i);
    expect(startInput.value).toBe('2023-05-15');
    expect(endInput.value).toBe('2026-05-15');
  });

  it('renders Daily and Weekly options', async () => {
    render(<BacktestPage />);
    await screen.findByLabelText(/price frequency/i);
    expect(screen.getByRole('option', { name: 'Daily' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Weekly' })).toBeInTheDocument();
  });

  it('allows selecting Weekly', async () => {
    render(<BacktestPage />);
    const select = await screen.findByLabelText<HTMLSelectElement>(/price frequency/i);
    fireEvent.change(select, { target: { value: '1w' } });
    expect(select.value).toBe('1w');
  });

  it('sends timeframe 1d when Daily is selected and Run Backtest is clicked', async () => {
    render(<BacktestPage />);
    await screen.findByLabelText(/price frequency/i);

    fireEvent.click(screen.getByRole('button', { name: /run backtest/i }));

    await waitFor(() =>
      expect(backtestApi.run).toHaveBeenCalledWith(
        expect.objectContaining({ timeframe: '1d' }),
      ),
    );
  });

  it('sends timeframe 1w when Weekly is selected and Run Backtest is clicked', async () => {
    render(<BacktestPage />);
    const select = await screen.findByLabelText<HTMLSelectElement>(/price frequency/i);
    fireEvent.change(select, { target: { value: '1w' } });

    fireEvent.click(screen.getByRole('button', { name: /run backtest/i }));

    await waitFor(() =>
      expect(backtestApi.run).toHaveBeenCalledWith(
        expect.objectContaining({ timeframe: '1w' }),
      ),
    );
  });
});

describe('BacktestPage — Optimize tab Price Frequency', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function openOptimizeTab() {
    render(<BacktestPage />);
    fireEvent.click(screen.getByRole('button', { name: /^optimize$/i }));
    await waitFor(() => expect(screen.getByLabelText(/price frequency/i)).toBeInTheDocument());
  }

  it('renders Price Frequency on Optimize tab defaulting to Daily', async () => {
    await openOptimizeTab();
    const select = screen.getByLabelText<HTMLSelectElement>(/price frequency/i);
    expect(select.value).toBe('1d');
  });

  it('sends timeframe 1w when Weekly is selected and Run Optimization is clicked', async () => {
    await openOptimizeTab();
    const select = screen.getByLabelText<HTMLSelectElement>(/price frequency/i);
    fireEvent.change(select, { target: { value: '1w' } });

    fireEvent.click(screen.getByRole('button', { name: /run optimization/i }));

    await waitFor(() =>
      expect(backtestApi.optimize).toHaveBeenCalledWith(
        expect.objectContaining({ timeframe: '1w' }),
      ),
    );
  });
});
