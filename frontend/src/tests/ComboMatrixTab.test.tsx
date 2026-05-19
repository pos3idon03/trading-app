import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ComboMatrixTab from '../components/ComboMatrixTab';
import type { AssetItem, ComboMatrixResponse } from '../api/types';
import * as endpoints from '../api/endpoints';
import { STRATEGIES } from '../constants/strategies';

const ASSETS: AssetItem[] = [
  {
    id: 1,
    symbol: 'AAPL',
    name: 'Apple Inc.',
    asset_type: 'equity',
    exchange: 'NASDAQ',
    currency: 'USD',
    is_active: true,
  },
];

const MOCK_MATRIX: ComboMatrixResponse = {
  asset_id: 1,
  strategies: ['ma_crossover', 'rsi', 'macd'],
  metric: 'sharpe_ratio',
  combination_mode: 'majority',
  values: [
    [1.0, 0.5, 0.3],
    [0.5, 1.2, 0.4],
    [0.3, 0.4, 0.9],
  ],
  duration_ms: 500,
};

describe('ComboMatrixTab', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders configuration form', () => {
    render(<ComboMatrixTab assets={ASSETS} />);
    expect(screen.getByText(/Strategy combination matrix/i)).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /ticker/i })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /metric/i })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /combination mode/i })).toBeInTheDocument();
  });

  it('disables run when fewer than 2 strategies selected', () => {
    render(<ComboMatrixTab assets={ASSETS} />);
    fireEvent.click(screen.getByRole('button', { name: /^none$/i }));
    const runBtn = screen.getByRole('button', { name: /run matrix/i });
    expect(runBtn).toBeDisabled();
  });

  it('calls runComboMatrix with expected payload on run', async () => {
    const spy = vi.spyOn(endpoints.backtestApi, 'runComboMatrix').mockResolvedValue(MOCK_MATRIX);
    render(<ComboMatrixTab assets={ASSETS} />);

    fireEvent.click(screen.getByRole('button', { name: /run matrix/i }));

    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    const payload = spy.mock.calls[0][0];
    expect(payload.symbol).toBe('AAPL');
    expect(payload.metric).toBe('sharpe_ratio');
    expect(payload.combination_mode).toBe('majority');
    expect(payload.strategies).toEqual(['ma_crossover', 'rsi', 'macd']);
    expect(payload.strategy_params).toBeDefined();
  });

  it('select all requires confirmation before selecting full catalog', () => {
    render(<ComboMatrixTab assets={ASSETS} />);
    fireEvent.click(screen.getByRole('button', { name: /run all strategies/i }));
    expect(screen.getByText(/Click "Run all strategies" again to confirm/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /confirm run all strategies/i })).toBeInTheDocument();
  });

  it('selects all strategies after confirmation', () => {
    render(<ComboMatrixTab assets={ASSETS} />);
    fireEvent.click(screen.getByRole('button', { name: /run all strategies/i }));
    fireEvent.click(screen.getByRole('button', { name: /confirm run all strategies/i }));
    expect(screen.getByText(new RegExp(`${STRATEGIES.length} selected`))).toBeInTheDocument();
  });

  it('renders heatmap after successful run', async () => {
    vi.spyOn(endpoints.backtestApi, 'runComboMatrix').mockResolvedValue(MOCK_MATRIX);
    render(<ComboMatrixTab assets={ASSETS} />);
    fireEvent.click(screen.getByRole('button', { name: /run matrix/i }));
    await waitFor(() => {
      expect(screen.getByRole('grid', { name: /strategy combination heatmap/i })).toBeInTheDocument();
    });
  });
});
