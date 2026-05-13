import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import StrategyBuilderPage from '../pages/StrategyBuilderPage';

vi.mock('../api/endpoints', () => ({
  dataApi: {
    getAssets: vi.fn().mockResolvedValue({
      assets: [
        { id: 1, symbol: 'AAPL', name: 'Apple Inc.', asset_type: 'stock', exchange: 'NASDAQ', currency: 'USD', is_active: true },
        { id: 2, symbol: 'MSFT', name: 'Microsoft', asset_type: 'stock', exchange: 'NASDAQ', currency: 'USD', is_active: true },
      ],
      count: 2,
    }),
  },
  strategyBuilderApi: {
    list: vi.fn().mockResolvedValue([]),
    create: vi.fn().mockResolvedValue({
      id: 10,
      asset_id: 1,
      symbol: 'AAPL',
      asset_name: 'Apple Inc.',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }),
    getFull: vi.fn().mockResolvedValue({
      strategy_id: 10,
      asset_id: 1,
      symbol: 'AAPL',
      asset_name: 'Apple Inc.',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      monte_carlo: null,
      ai_agents: null,
      financials: null,
      algo_strategies: [],
      monte_carlo_error: null,
      ai_agents_error: null,
      financials_error: null,
    }),
    remove: vi.fn().mockResolvedValue({ deleted: true }),
    attachBacktest: vi.fn().mockResolvedValue({}),
    detachBacktest: vi.fn().mockResolvedValue({}),
  },
}));

describe('StrategyBuilderPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page heading', async () => {
    render(<StrategyBuilderPage />);
    expect(screen.getByText('Strategy Builder')).toBeInTheDocument();
  });

  it('shows empty state when no strategies', async () => {
    render(<StrategyBuilderPage />);
    await waitFor(() => {
      expect(screen.getByText(/No strategies yet/i)).toBeInTheDocument();
    });
  });

  it('renders strategy cards when strategies exist', async () => {
    const { strategyBuilderApi } = await import('../api/endpoints');
    (strategyBuilderApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      {
        id: 10, asset_id: 1, symbol: 'AAPL', asset_name: 'Apple Inc.',
        is_active: true, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
      },
    ]);

    render(<StrategyBuilderPage />);
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument();
    });
  });

  it('create form has a disabled button when no asset selected', async () => {
    render(<StrategyBuilderPage />);
    await waitFor(() => screen.getByText('Create Strategy'));
    const button = screen.getByRole('button', { name: /Create Strategy/i });
    expect(button).toBeDisabled();
  });
});
