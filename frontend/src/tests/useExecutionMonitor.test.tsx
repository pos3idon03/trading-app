import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useExecutionMonitor, TRANSACTIONS_PAGE_SIZE } from '../hooks/useExecutionMonitor';
import type { AutoTradingAssetRow, OrderItem } from '../api/types';

const runningAsset: AutoTradingAssetRow = {
  strategy_id: 1,
  asset_id: 10,
  symbol: 'BTCUSD',
  asset_name: 'Bitcoin',
  asset_type: 'crypto',
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
  algo_timeframe: '1d',
  auto_trading_started: true,
  max_amount_per_position: null,
  max_pct_of_capital: null,
};

const mockOrder: OrderItem = {
  id: 1,
  symbol: 'BTCUSD',
  side: 'buy',
  qty: 0.1,
  order_type: 'market',
  limit_price: null,
  stop_price: null,
  status: 'filled',
  alpaca_order_id: 'alp-1',
  filled_price: 100,
  filled_qty: 0.1,
  filled_at: '2026-05-16T12:00:00Z',
  signal_id: null,
  error_message: null,
  created_at: '2026-05-16T11:59:00Z',
  updated_at: '2026-05-16T12:00:00Z',
};

vi.mock('../api/endpoints', () => ({
  autoTradingApi: { list: vi.fn() },
  executionApi: { getOrders: vi.fn() },
  liveApi: { getIndicators: vi.fn(), getStrategySignals: vi.fn() },
  strategyBuilderApi: { getFull: vi.fn() },
}));

describe('useExecutionMonitor', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const { autoTradingApi, executionApi, liveApi, strategyBuilderApi } = await import('../api/endpoints');

    (autoTradingApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([runningAsset]);
    (executionApi.getOrders as ReturnType<typeof vi.fn>).mockResolvedValue({
      orders: [mockOrder],
      total: 25,
    });
    (liveApi.getIndicators as ReturnType<typeof vi.fn>).mockResolvedValue({
      close_price: 100,
      created_at: '2026-05-16T12:00:00Z',
    });
    (liveApi.getStrategySignals as ReturnType<typeof vi.fn>).mockResolvedValue({ strategies: [] });
    (strategyBuilderApi.getFull as ReturnType<typeof vi.fn>).mockResolvedValue({ algo_strategies: [] });
  });

  it('fetches first page of orders with limit 10 and offset 0', async () => {
    const { executionApi } = await import('../api/endpoints');
    const { result } = renderHook(() => useExecutionMonitor());

    await waitFor(() => {
      expect(result.current.monitors).toHaveLength(1);
    });

    expect(executionApi.getOrders).toHaveBeenCalledWith('BTCUSD', TRANSACTIONS_PAGE_SIZE, 0);
    expect(result.current.monitors[0].orders).toHaveLength(1);
    expect(result.current.monitors[0].ordersTotal).toBe(25);
    expect(result.current.monitors[0].ordersPage).toBe(1);
  });

  it('fetches page 2 when setOrdersPage is called', async () => {
    const { executionApi } = await import('../api/endpoints');
    (executionApi.getOrders as ReturnType<typeof vi.fn>).mockImplementation(
      async (_symbol: string, _limit: number, offset: number) => ({
        orders: offset === 0 ? [mockOrder] : [{ ...mockOrder, id: 2 }],
        total: 25,
      }),
    );

    const { result } = renderHook(() => useExecutionMonitor());

    await waitFor(() => {
      expect(result.current.monitors).toHaveLength(1);
    });

    await act(async () => {
      await result.current.setOrdersPage(1, 2);
    });

    await waitFor(() => {
      expect(result.current.monitors[0].ordersPage).toBe(2);
    });

    expect(executionApi.getOrders).toHaveBeenLastCalledWith(
      'BTCUSD',
      TRANSACTIONS_PAGE_SIZE,
      TRANSACTIONS_PAGE_SIZE,
    );
    expect(result.current.monitors[0].orders[0].id).toBe(2);
  });
});
