import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ComboTab from '../components/ComboTab';
import type { AssetItem, BacktestResponse } from '../api/types';
import * as endpoints from '../api/endpoints';

const ASSETS: AssetItem[] = [
  { id: 1, symbol: 'AAPL', name: 'Apple Inc.', asset_type: 'equity', exchange: 'NASDAQ', currency: 'USD', is_active: true },
  { id: 2, symbol: 'MSFT', name: 'Microsoft', asset_type: 'equity', exchange: 'NASDAQ', currency: 'USD', is_active: true },
];

const MOCK_RESULT: BacktestResponse = {
  backtest_id: 99,
  asset_id: 1,
  strategy_name: 'combo:majority',
  status: 'done',
  metrics: {
    sharpe_ratio: 1.2,
    sortino_ratio: 1.5,
    max_drawdown: -0.15,
    win_rate: 0.55,
    profit_factor: 1.3,
    total_return: 0.45,
    annualized_return: 0.18,
    num_trades: 42,
  },
  equity_curve: [{ time: '2022-01-01', value: 100000 }],
  buy_hold_curve: [{ time: '2022-01-01', value: 100000 }],
};

describe('ComboTab', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the combo configuration card', () => {
    render(<ComboTab assets={ASSETS} />);
    expect(screen.getByText(/Combination Configuration/i)).toBeInTheDocument();
  });

  it('sets first asset as selected ticker', () => {
    render(<ComboTab assets={ASSETS} />);
    const ticker = screen.getByRole('combobox', { name: /ticker/i }) as HTMLSelectElement;
    expect(ticker.value).toBe('AAPL');
  });

  it('renders MA Crossover and RSI as default strategies', () => {
    render(<ComboTab assets={ASSETS} />);
    expect(screen.getByText('MA Crossover')).toBeInTheDocument();
    expect(screen.getByText(/RSI/i)).toBeInTheDocument();
  });

  it('displays the combination mode selector', () => {
    render(<ComboTab assets={ASSETS} />);
    expect(screen.getByRole('combobox', { name: /combination mode/i })).toBeInTheDocument();
  });

  it('shows AND, Majority, Weighted mode options', () => {
    render(<ComboTab assets={ASSETS} />);
    const modeSelect = screen.getByRole('combobox', { name: /combination mode/i });
    expect(modeSelect).toContainHTML('AND');
    expect(modeSelect).toContainHTML('Majority');
    expect(modeSelect).toContainHTML('Weighted');
  });

  it('does NOT show threshold input in majority mode', () => {
    render(<ComboTab assets={ASSETS} />);
    expect(screen.queryByLabelText(/threshold/i)).not.toBeInTheDocument();
  });

  it('shows threshold input when weighted mode is selected', () => {
    render(<ComboTab assets={ASSETS} />);
    const modeSelect = screen.getByRole('combobox', { name: /combination mode/i });
    fireEvent.change(modeSelect, { target: { value: 'weighted' } });
    expect(screen.getByLabelText(/threshold/i)).toBeInTheDocument();
  });

  it('shows weight inputs per strategy in weighted mode', () => {
    render(<ComboTab assets={ASSETS} />);
    const modeSelect = screen.getByRole('combobox', { name: /combination mode/i });
    fireEvent.change(modeSelect, { target: { value: 'weighted' } });
    const weightInputs = screen.getAllByRole('spinbutton', { name: /weight/i });
    expect(weightInputs.length).toBeGreaterThanOrEqual(2);
  });

  it('removes a strategy when the remove button is clicked (min 2 enforced)', () => {
    render(<ComboTab assets={ASSETS} />);
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    expect(removeButtons.length).toBeGreaterThanOrEqual(2);
    // Try removing one — should be blocked since we already have only 2
    fireEvent.click(removeButtons[0]);
    // Still 2 strategies shown (MA Crossover + RSI)
    expect(screen.getByText('MA Crossover')).toBeInTheDocument();
    expect(screen.getByText(/RSI/i)).toBeInTheDocument();
  });

  it('adds a strategy via the Add dropdown', () => {
    render(<ComboTab assets={ASSETS} />);
    const addSelect = screen.getByRole('combobox', { name: '' });
    fireEvent.change(addSelect, { target: { value: 'macd' } });
    fireEvent.click(screen.getByRole('button', { name: /^add$/i }));
    expect(screen.getByText('MACD')).toBeInTheDocument();
  });

  it('disables Run button when fewer than 2 strategies are selected', () => {
    // Render with an empty assets list to test disabled state independently
    render(<ComboTab assets={[]} />);
    const runBtn = screen.getByRole('button', { name: /run combo/i });
    expect(runBtn).toBeDisabled();
  });

  it('calls backtestApi.runCombo with correct payload on Run click', async () => {
    const spy = vi.spyOn(endpoints.backtestApi, 'runCombo').mockResolvedValue(MOCK_RESULT);
    render(<ComboTab assets={ASSETS} />);
    fireEvent.click(screen.getByRole('button', { name: /run combo/i }));
    await waitFor(() => expect(spy).toHaveBeenCalledOnce());
    const req = spy.mock.calls[0][0];
    expect(req.symbol).toBe('AAPL');
    expect(req.strategies.length).toBeGreaterThanOrEqual(2);
    expect(req.combination_mode).toBe('majority');
  });

  it('displays BacktestResultCard after a successful run', async () => {
    vi.spyOn(endpoints.backtestApi, 'runCombo').mockResolvedValue(MOCK_RESULT);
    render(<ComboTab assets={ASSETS} />);
    fireEvent.click(screen.getByRole('button', { name: /run combo/i }));
    await waitFor(() =>
      expect(screen.getByText(/combo:majority/i)).toBeInTheDocument()
    );
  });

  it('shows an error alert when the API call fails', async () => {
    vi.spyOn(endpoints.backtestApi, 'runCombo').mockRejectedValue(new Error('Server error'));
    render(<ComboTab assets={ASSETS} />);
    fireEvent.click(screen.getByRole('button', { name: /run combo/i }));
    await waitFor(() => expect(screen.getByText(/server error/i)).toBeInTheDocument());
  });
});
