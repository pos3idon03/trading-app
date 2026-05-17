import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useLiveStreamSync } from '../hooks/useLiveStreamSync';
import type { ExecutionAssetMonitor } from '../api/types';

vi.mock('../api/endpoints', () => ({
  liveApi: {
    getStatus: vi.fn(),
    startStream: vi.fn(),
  },
}));

const stockMonitor: ExecutionAssetMonitor = {
  strategyId: 1,
  symbol: 'AAPL',
  assetName: 'Apple',
  assetType: 'stock',
  combinationMode: 'all',
  algoTimeframe: '5m',
  criteria: [],
  overallSignal: 'NEUTRAL',
  algoSignals: [],
  comboSignals: [],
  latestPrice: 100,
  priceUpdatedAt: null,
  lastLivePollAt: null,
  indicatorSnapshot: null,
  orders: [],
  ordersTotal: 0,
  ordersPage: 1,
  loading: false,
  error: null,
};

const cryptoMonitor: ExecutionAssetMonitor = {
  ...stockMonitor,
  strategyId: 2,
  symbol: 'BTC-USD',
  assetType: 'crypto',
};

describe('useLiveStreamSync', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const { liveApi } = await import('../api/endpoints');
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
      subscribed_symbols: ['AAPL', 'BTC-USD'],
      last_tick_at: null,
      error: null,
      reconnect_count: 0,
    });
  });

  it('starts stream for all running symbols including crypto', async () => {
    const { liveApi } = await import('../api/endpoints');
    const onStreamEvent = vi.fn();

    renderHook(() =>
      useLiveStreamSync([stockMonitor, cryptoMonitor], { onStreamEvent }),
    );

    await waitFor(() => {
      expect(liveApi.startStream).toHaveBeenCalledWith(
        expect.objectContaining({ symbols: ['AAPL', 'BTC-USD'] }),
      );
    });

    expect(onStreamEvent).toHaveBeenCalledWith(
      expect.stringContaining('Alpaca stream connected'),
      'info',
    );
  });
});
