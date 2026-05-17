import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LiveTradingPage from '../pages/LiveTradingPage';
import type { AutoTradingAssetRow } from '../api/types';

const runningAsset: AutoTradingAssetRow = {
  strategy_id: 1,
  asset_id: 10,
  symbol: 'AAPL',
  asset_name: 'Apple Inc.',
  asset_type: 'stock',
  mc_prob_positive: 0.7,
  mc_buy_prob_positive: 0.65,
  mc_sell_prob_positive: 0.4,
  ai_conviction: 0.8,
  ai_sentiment: 0.3,
  ai_macro: 0.2,
  ai_buy_conviction: 0.7,
  ai_sell_conviction: 0.3,
  ai_buy_sentiment: 0.2,
  ai_sell_sentiment: -0.1,
  ai_buy_macro: 0.1,
  ai_sell_macro: -0.2,
  combination_mode: 'all',
  algo_timeframe: '1h',
  auto_trading_started: true,
  max_amount_per_position: null,
  max_pct_of_capital: null,
};

vi.mock('../api/endpoints', () => ({
  autoTradingApi: { list: vi.fn() },
  executionApi: { getOrders: vi.fn() },
  liveApi: {
    getStatus: vi.fn(),
    startStream: vi.fn(),
    getIndicators: vi.fn(),
    getStrategySignals: vi.fn(),
  },
  strategyBuilderApi: { getFull: vi.fn() },
}));

describe('LiveTradingPage', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const { autoTradingApi, executionApi, liveApi, strategyBuilderApi } = await import('../api/endpoints');

    (autoTradingApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([runningAsset]);
    (executionApi.getOrders as ReturnType<typeof vi.fn>).mockResolvedValue({ orders: [], total: 0 });
    (liveApi.getStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      connected: false,
      stock_connected: false,
      crypto_connected: false,
      subscribed_symbols: [],
      last_tick_at: null,
      error: null,
      reconnect_count: 0,
    });
    (liveApi.startStream as ReturnType<typeof vi.fn>).mockResolvedValue({
      connected: true,
      stock_connected: true,
      crypto_connected: true,
      subscribed_symbols: ['AAPL'],
      last_tick_at: null,
      error: null,
      reconnect_count: 0,
    });
    (liveApi.getIndicators as ReturnType<typeof vi.fn>).mockResolvedValue({
      symbol: 'AAPL',
      timeframe: '1h',
      close_price: 175.5,
      created_at: '2026-05-16T12:00:00Z',
    });
    (liveApi.getStrategySignals as ReturnType<typeof vi.fn>).mockResolvedValue({
      symbol: 'AAPL',
      timeframe: '1h',
      bar_count: 60,
      strategies: [],
    });
    (strategyBuilderApi.getFull as ReturnType<typeof vi.fn>).mockResolvedValue({ algo_strategies: [] });
  });

  it('renders the page heading and terminal description', () => {
    render(<LiveTradingPage />);
    expect(screen.getByText('Live Trading')).toBeInTheDocument();
    expect(screen.getByText(/Terminal log of auto-trading activity/i)).toBeInTheDocument();
  });

  it('shows empty state when no auto-trading assets are running', async () => {
    const { autoTradingApi } = await import('../api/endpoints');
    (autoTradingApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    render(<LiveTradingPage />);
    await waitFor(() => {
      expect(screen.getByText(/No auto-trading assets are currently running/i)).toBeInTheDocument();
    });
  });

  it('shows stream status and auto-starts for stock assets', async () => {
    const { liveApi } = await import('../api/endpoints');
    render(<LiveTradingPage />);
    await waitFor(() => {
      expect(screen.getByTestId('stream-status')).toHaveTextContent(/connected/i);
    });
    expect(liveApi.startStream).toHaveBeenCalled();
  });

  it('shows activity terminal when assets are running', async () => {
    render(<LiveTradingPage />);
    await waitFor(() => {
      expect(screen.getByTestId('activity-terminal')).toBeInTheDocument();
    });
  });

  it('clear log button removes visible activity lines after criteria refresh', async () => {
    const user = userEvent.setup();
    const { autoTradingApi } = await import('../api/endpoints');
    let mcProb = 0.7;
    (autoTradingApi.list as ReturnType<typeof vi.fn>).mockImplementation(async () => [
      { ...runningAsset, mc_prob_positive: mcProb },
    ]);

    render(<LiveTradingPage />);
    await waitFor(() => {
      expect(screen.getByTestId('activity-terminal')).toBeInTheDocument();
    });

    mcProb = 0.71;
    await user.click(screen.getByRole('button', { name: /^Refresh$/i }));

    await waitFor(() => {
      expect(screen.getByText(/MC Prob\+ updated/)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Clear log/i }));

    await waitFor(() => {
      expect(screen.queryByText(/MC Prob\+/)).not.toBeInTheDocument();
    });
  });
});
